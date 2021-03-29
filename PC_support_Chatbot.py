#!C:/Program Files (x86)/Microsoft Visual Studio/Shared/Python36_64/python.exe
# -*- coding: utf-8 -*-
# ライブラリのパスを上書きする記述
from __future__ import print_function, unicode_literals
import sys
#sys.path.append("C:\\Program Files (x86)\\Microsoft Visual Studio\\Shared\\Python36_64\\Lib\\urllib")
import MeCab
import sys
sys.path.append("C:\\Program Files (x86)\\Microsoft Visual Studio\\Shared\\Python36_64\\Lib\\urllib")
from urllib.parse import urlparse
import mysql.connector
import json
url = urlparse('mysql://@localhost:3306/qa_db')
import requests
import pprint
import json



class Chat(): #Chatwork module
    APIKEY = '' #the class variables for the module
    ENDPOINT = 'https://api.chatwork.com/v2'
    ###ROOMID = '' #ID of the chatroom
    ROOMID = ''
    SELFID= ''  #ID of the chatwork bot

    def NewJson(self, f): #to clean up the existing JSON for the mecab module
        list=[]
        for n in f:
            MSGID= n['message_id'] #Extracting only relevant info
            ACCID=n['account']['account_id']
            content= n['body']
            dic= {'MSGID': MSGID, 'ACCID': ACCID, 'Content': content}
            list.append(dic)
        return list
    
    def getMessage(self): #retrieve new messages from the room
        get_message_url = '{}/rooms/{}/messages'.format(self.ENDPOINT, self.ROOMID) #defining room url
        #resp=requests.get(get_message_url,headers={'X-ChatWorkToken': APIKEY},params=param)
        resp=requests.get(get_message_url,headers={'X-ChatWorkToken': self.APIKEY}) #Get request
        #pprint.pprint(resp.content)
        if(resp.status_code==200): #Checking if request was successful
            new_resp = resp.content.decode('utf-8') 
            d = json.dumps(new_resp) #Converting to JSON
            new_d= json.loads(d)
            f= json.loads(new_d)
            new_f= self.NewJson(f) #Cleaning JSON
            return new_f
        else:
            return None

    def postMessage(self,mid,acid,ans): #Post answers
        MSGID=''
        ACCID=''

        MSGID = mid #Message ID
        ACCID = acid #Account to which you are replying

        post_message_url = '{}/rooms/{}/messages'.format(self.ENDPOINT, self.ROOMID)
        headers = { 'X-ChatWorkToken': self.APIKEY }
        if(str(ACCID)!=self.SELFID): #To not reply to the bot itself
            params = { 'body': '[rp aid={} to={}-{}]'.format(ACCID,self.ROOMID,MSGID)+ ans} 
            resp = requests.post(post_message_url, headers=headers, params=params) #Post request

# Class for connecting to the database. 
# Takes hostname, port, username, password, database name as arguments.
# This class can be used to connect to the Database, get all questions in DB and Get answer to a given question
# with its ID.

class DB_connect:

    def __init__(self,host,port,user,pwd,db_name):
        self.hostname = url.hostname or host
        self.port = url.port or port
        self.user = url.username or user
        self.password = pwd
        self.database = url.path[1:] or db_name

	# Method to connect to the Database. Returns the connection object.
    def connect_to_db(self):
        conn = mysql.connector.connect(
            host = self.hostname,
            port = self.port,
            user = self.user,
            password = self.password,
            database = self.database,
        )
        return conn

	# Method to get all the questions from the Database. Returns a list of ID and Question in Json format. 
    def get_all_questions(self):
        conn = self.connect_to_db();
        cur = conn.cursor()
        cur.execute('SELECT * FROM qa_table')
        result = cur.fetchall()
        items = []
        for row in result:
            items.append({'id':row[0],'question':row[1]})
        cur.close()
        conn.close()
        return json.dumps(items)

	# Given a question ID, Fetches answer from the database. Returns a list of Step number and the corresponding
	# line in Json format.
    def get_answer_by_questionID(self,id):
        conn = self.connect_to_db();
        cur = conn.cursor()
        cur.execute("SELECT step,point FROM answer_table where question_id = '%s'", (id, ))
        result = cur.fetchall()
        items = []
        for row in result:
            items.append({'step':row[0],'point':row[1]})
        cur.close()
        conn.close()
        return json.dumps(items)



'''
Class containing methods for performing Mecab related operations - sentence splitting, extracting word context and comparing questions to find similarity
'''
class mekabu:

    '''
    Initialise class instance. Define member variables to use for preprocessing and parts of speech extraction
    '''
    def __init__(self):
        self.verb = '動詞'
        self.noun = '名詞'
        self.adjective = '形容詞'
        self.adjverb = '形容動詞'
        self.deter = '連体詞'

        self.specialchars = ['」', '「', '『', '』', '（', '）', '〔', '〕', '［', '］', '｛', '｝', '｟', '｠', '〈', '〉', '《', '》', '【', '】', '〖', '〗','〘', '〙', '〚', '〛']

    '''
    Method to remove special character such as quotation marks and braces from question
    '''
    def preprocess(self, str):
        for c in str:
            if(c in self.specialchars):
                str = str.replace(c, "")
        return str

    '''
    Method to split the sentence into its constituent words and their corresponding parts of speech and return a list containing the Mecab split data of the sentence. 
    Mecab library calls are used to do the same
    '''
    def mecab_list(self, text):
        tagger = MeCab.Tagger("-Ochasen")
        tagger.parse('')
        node = tagger.parseToNode(text)
        word_class = []
        while node:
            word = node.surface
            wclass = node.feature.split(',')
            if wclass[0] != u'BOS/EOS':
                if wclass[6] == None:
                    word_class.append((word,wclass[0],wclass[1],wclass[2],""))
                else:
                    word_class.append((word,wclass[0],wclass[1],wclass[2],wclass[6]))
            node = node.next
        return word_class

    '''
    Returns a list of all the words of a sentence having the same type (part of speech). Also filters common words such as 'the' which may give an inaccurate similarity count
    '''
    def getwords(self, sentence, type):
        lst = []
        for word in sentence:
            if(word[1] == type and word[0] != 'し' and word[0] != 'さ' and word[0] != 'れ'):
                if([word[0], word[1]] not in lst):
                    lst.append([word[0], word[1]])

        return lst

    '''
    Returns a count of similarity by counting equal words of the same type (part of speech) between two sentences
    '''
    def compare(self, q1, q2):
        cnt=0
        for w1 in q1:
            for w2 in q2:
                if(w1[0] == w2[0]):
                    cnt += 1
        return cnt

    '''
    Performs Mecab splitting for all the pre existing questions from the database
    '''
    def getdbanalysis(self, lst):
        ana = []
        for s in lst:
            s["question"] = self.preprocess(s["question"])
            test = self.mecab_list(s["question"])
            ana.append((s["id"], test)) 
        return ana

    '''
    The core function. Iterates through all the questions in the database and returns the index associated with the question that is most similar to the one received from the helpline chatroom. If the similarity is less than 2, it returns a negative flag.
    '''
    def most_similar(self, ques, lst):

        ques = self.preprocess(ques)

        q = self.mecab_list(ques)
        ana = self.getdbanalysis(lst)   

        qverbs = self.getwords(q, self.verb)
        qnouns = self.getwords(q, self.noun)
        qadjectives = self.getwords(q, self.adjective)
        qadjverbs = self.getwords(q, self.adjverb)
        qdeters = self.getwords(q, self.deter)
    
        max = -1
        maxindex = -1

        for e in ana:
        
            a = e[1]
        
            verblist = self.getwords(a, self.verb)
            verbcount = self.compare(qverbs, verblist)
        
            nounlist = self.getwords(a, self.noun)
            nouncount = self.compare(qnouns, nounlist)


            adjectivelist = self.getwords(a, self.adjective)
            adjectivecount = self.compare(qadjectives, adjectivelist)

            adjverblist = self.getwords(a, self.adjverb)
            adjverbcount = self.compare(qadjverbs, adjverblist)
        
            deterlist = self.getwords(a, self.deter)
            detercount = self.compare(qdeters, deterlist)


            totcount = adjverbcount + adjectivecount + detercount + nouncount + verbcount
            if(totcount > max):
                max = totcount
                maxindex = e[0]
        
        if(max >= 2):
            return maxindex
        return -1


    '''
    Driver function to receive database questions, recieve index of most similar question, retrieve the corresponding answer and post the same to the chatroom
    '''
    def process_question(self,x,DB_object,chat):
        lst = json.loads(DB_object.get_all_questions())

        for n in x:
            ques = n['Content']
            mostsim = ob.most_similar(ques,lst)
            if(mostsim > -1):
                print (str(lst[mostsim-1]["id"]) + " " + lst[mostsim-1]["question"])
                res = json.loads(DB_object.get_answer_by_questionID(lst[mostsim-1]["id"]))
                answer_str = ""
                for line in res:
                    answer_str += line["point"] + "\n"
                chat.postMessage(n['MSGID'],n['ACCID'],answer_str)
            else:
                answer_str = "No matching question in Database. Please re-enter"
                chat.postMessage(n['MSGID'],n['ACCID'],answer_str)



ob = mekabu()

chat = Chat()
DB_object = DB_connect('localhost',3306,'root','welcome@2018','qa_db')

x = chat.getMessage()
if(x!=None):
    ob.process_question(x,DB_object,chat)



