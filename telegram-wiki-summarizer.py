import nltk
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
import networkx as nx
from bs4 import BeautifulSoup
from sys import argv
from requests import get
import telebot
from os import environ
from dotenv import load_dotenv

load_dotenv()
API_KEY = environ.get('API_KEY')
bot = telebot.TeleBot(token = API_KEY)

@bot.message_handler(commands=['Greet'])
def greet(message):
    bot.reply_to(message,"Hey! How its going")

bot.polling()
