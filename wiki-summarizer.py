from logging import error
import nltk
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
import networkx as nx
from bs4 import BeautifulSoup
from sys import argv
from requests import get,head
import telebot
from os import environ
import re
from dotenv import load_dotenv
 
load_dotenv()
API_KEY = environ.get('API_KEY')
bot = telebot.TeleBot(token = API_KEY)

def valid_site(url):
    r = head(f"{url}")
    if r.status_code == 200:
        return True
    elif 400 <= r.status_code < 500:
        return False
    else:
        return None

def get_title(url):
    res = get(url + ' '.join(argv[1:]))
    res.raise_for_status()
    wiki = BeautifulSoup(res.text,"lxml")
    title = wiki.title.get_text()

    return title

def read_article(url):
    try:
        res = get(url + ' '.join(argv[1:]))
        res.raise_for_status()
    except:
        return ValueError
    wiki = BeautifulSoup(res.text,"lxml")
    article = wiki.select("p")
    sentences = []
    
    for i in range(len(article)):
        print(article[i].getText())
        text = re.sub(r'\[[0-9]*\]', ' ', article[i].getText())
        if (text == '\n' or text == ' '):
            continue
        sentences.append(text.replace("[^a-zA-Z]", " ").split(" "))
    sentences.pop() 

    return sentences

def sentence_similarity(sent1, sent2, stopwords=None):
    if stopwords is None:
        stopwords = []
 
    sent1 = [w.lower() for w in sent1]
    sent2 = [w.lower() for w in sent2]
 
    all_words = list(set(sent1 + sent2))
 
    vector1 = [0] * len(all_words)
    vector2 = [0] * len(all_words)
 
    # build the vector for the first sentence
    for w in sent1:
        if w in stopwords:
            continue
        vector1[all_words.index(w)] += 1
 
    # build the vector for the second sentence
    for w in sent2:
        if w in stopwords:
            continue
        vector2[all_words.index(w)] += 1
 
    return 1 - cosine_distance(vector1, vector2)
 
def build_similarity_matrix(sentences, stop_words):
    # Create an empty similarity matrix
    similarity_matrix = np.zeros((len(sentences), len(sentences)))
 
    for idx1 in range(len(sentences)):
        for idx2 in range(len(sentences)):
            if idx1 == idx2: #ignore if both are same sentences
                continue 
            
            similarity_matrix[idx1][idx2] = sentence_similarity(sentences[idx1], sentences[idx2], stop_words)

    return similarity_matrix

def generate_summary(url, top_n=5):
    nltk.download("stopwords")
    stop_words = stopwords.words('english')
    
    summarize_text = []

    # Step 1 - Read text anc split it
    sentences =  read_article(url)

    # Step 2 - Generate Similary Martix across sentences
    sentence_similarity_martix = build_similarity_matrix(sentences, stop_words)

    # Step 3 - Rank sentences in similarity martix
    sentence_similarity_graph = nx.from_numpy_array(sentence_similarity_martix)
    scores = nx.pagerank(sentence_similarity_graph)

    # Step 4 - Sort the rank and pick top sentences
    ranked_sentence = sorted(((scores[i] if i!=0 else 1,s) for i,s in enumerate(sentences)), reverse=True)    
    print("Indexes of top ranked_sentence order are ", ranked_sentence)    

    for i in range(top_n):
      summarize_text.append(" ".join(ranked_sentence[i][1]))

    # Step 5 - Return the summarize text
    return (summarize_text)

@bot.message_handler(commands=['start','help','Start','Help','START','HELP'])
def greet(message):
    greet = (f"Hello {message.from_user.username},\nWikipedia Summarizer Bot this side.\nHere you can send" +
            " link of any wikipedia article to summarize it.\nThis bot is created by Gurman Singh.\nThank You for using it")
    bot.send_message(message.chat.id, greet)

@bot.message_handler(regexp="(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?")
def handle_text_doc(message):
    try:
        url = re.search("(?P<url>https?://[^\s]+)", message.text).group("url")
        print(url)
    except :
        print("Error reading url")
    else:
        if (valid_site(url)):
            splitted = telebot.util.split_string(generate_summary(url,3),3000)
            title = get_title(url)
            bot.send_message(message.chat.id, f"Summary of {title}:")

            for text in splitted[0]:
                text = re.sub(r' +',' ',text)
                print(text)
                bot.send_message(message.chat.id, text)
        else:
            bot.send_message(message.chat.id, "Your Link is broken please check it")


@bot.message_handler(func = lambda message: True, content_types=['audio','photo','voice',
                                                                'video','document','contact',
                                                                'text','location','sticker'])
def default_message(message):
    bot.send_message(message.chat.id, "Command Not recognised")

# let's begin
if __name__ == "__main__":
    bot.polling()
