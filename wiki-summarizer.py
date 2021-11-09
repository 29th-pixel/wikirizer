from fpdf import FPDF
import nltk
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
import networkx as nx
from bs4 import BeautifulSoup
from sys import argv
from requests import get,head
import telebot
import os
import re
from dotenv import load_dotenv
import time
import textwrap
from PIL import Image, ImageFont, ImageDraw
 
load_dotenv()
API_KEY = os.environ.get('API_KEY')
bot = telebot.TeleBot(token = API_KEY)

def valid_site(url):
    """This Functions checks if the given url exists or not

    Args:
        url (string): Link given by the user

    Returns:
        bool: returns true if url is valid
    """
    r = head(f"{url}")
    if r.status_code == 200:
        return True
    elif 400 <= r.status_code < 500:
        return False
    else:
        return None

def get_title(url):
    """Gets the title from the url

    Args:
        url (string): url given by user

    Returns:
        string: title string is return
    """
    res = get(url + ' '.join(argv[1:]))
    res.raise_for_status()
    wiki = BeautifulSoup(res.text,"lxml")
    title = wiki.title.get_text()
    return title

def read_article(url):
    """Scrape the contents from the url

    Args:
        url (string): url passed by user

    Returns:
        list: list of sentences in the web page
    """
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
        text = re.sub(r' +',' ',text)
        if (text == '\n' or text == ' '):
            continue
        sentences.append(text.replace("[^a-zA-Z]", " ").split(" "))
    sentences.pop() 

    return sentences

def sentence_similarity(sent1, sent2, stopwords=None):
    """Generates the sentence similarity vector

    Args:
        sent1 (string): Sentence 1
        sent2 (string): Sentence 2
        stopwords (list, optional): list of stopwords. Defaults to None.

    Returns:
        float: vector of sentence similarity
    """
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
    """Build similarity @2D matrix 

    Args:
        sentences (list): List of sentences 
        stop_words (list): list of stop words

    Returns:
        array: similarity matrix
    """
    # Create an empty similarity matrix
    similarity_matrix = np.zeros((len(sentences), len(sentences)))
 
    for idx1 in range(len(sentences)):
        for idx2 in range(len(sentences)):
            if idx1 == idx2: #ignore if both are same sentences
                continue 
            similarity_matrix[idx1][idx2] = sentence_similarity(sentences[idx1], sentences[idx2], stop_words)

    return similarity_matrix

def generate_summary(url, top_n=5):
    """Selects important paragraphs to put in summary

    Args:
        url (string): Url given by user
        top_n (int, optional): Number of top paragraphs required. Defaults to 5.

    Returns:
        list: list of selected paragraphes
    """
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

def export_summary(message):
    """give user options to export in Image, Text or PDF file

    Args:
        message (object): message object of telebot
    """
    bot.send_message(message.chat.id, (f"{message.from_user.username}, You can export this summary to\nText document"+ 
                    "\nImage and \nPDF"))
    bot.send_message(message.chat.id, "Choose any of the above options")
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)

    itembtn1 = telebot.types.KeyboardButton('Text File')
    itembtn2 = telebot.types.KeyboardButton('Image')
    itembtn3 = telebot.types.KeyboardButton('PDF')
    itembtn4 = telebot.types.KeyboardButton('None')
    
    markup.add(itembtn1, itembtn2, itembtn3,itembtn4)
    bot.send_message(message.chat.id, "Choose one letter:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Text File')
def exportText(message):
    """Exports the summary in .txt file and then sends it to the user

    Args:
        message (object)
    """
    bot.send_message(message.chat.id, "Your text file is being processed")
    file_name = time.strftime("%Y%m%d-%H%M%S") + ".txt"
    file = open(file_name,'w', encoding="utf-8")

    try:
        file.write(handle_text_doc.title + '\n')
        for text in handle_text_doc.splitted[0]:
            if len(text)>1 or text != '\n':
                file.write(str(text)+'\n')
        file.close()
    
    except:
        bot.send_message(message.chat.id, "Error No URL is passed")
    else: 
        file = open(file_name,'rb')
        bot.send_message(message.chat.id, "File processing completed")
        bot.send_document(message.chat.id, data=file)
    
    file.close()
    os.remove(file_name)

@bot.message_handler(func=lambda message: message.text == 'PDF')
def exportPDF(message):
    """Exports the summary in .pdf format and sends it to the user.

    Args:
        message (object)
    """
    bot.send_message(message.chat.id, "Your text file is being processed")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times",style='B', size = 16)
    file_name = time.strftime("%Y%m%d-%H%M%S") + ".pdf"
    try:
        pdf.cell(200, 7.5, txt = f"Summary - {handle_text_doc.title}", ln = 1, align = 'C')
        pdf.set_font("Times", size = 12)
        for text in handle_text_doc.splitted[0]:
            text2 = text.encode('latin-1', 'ignore').decode('latin-1')
            pdf.multi_cell(200, 5, txt = text2, align = 'L')
        pdf.output(file_name)
    except UnicodeEncodeError:
        bot.send_message(message.chat.id,"Can't export this summary to PDF due to decoding error")
    except AttributeError:
        bot.send_message(message.chat.id, "Error No URL is passed")
    else:
        bot.send_message(message.chat.id, "File processing completed")
        bot.send_document(message.chat.id, data = open(file_name,'rb'))
        os.remove(file_name)

@bot.message_handler(func= lambda message: message.text == 'Image')
def exportImage(message):
    """Exports the summary written on black white image in .png format and sends it to the 
        user

    Args:
        message (object)
    """
    bot.send_message(message.chat.id, "Your text file is being processed")
    img = Image.new('RGB', (1920, 1080), color='white')
    Font = ImageFont.truetype('Roboto[wdth,wght].ttf', size = 80)
    draw = ImageDraw.Draw(img)
    y_text = 50
    img_exist = False

    try:
        line_width, line_height = Font.getsize(f"Summary - {handle_text_doc.title}")
        draw.text(((1920 - line_width) / 2, y_text), f"Summary - {handle_text_doc.title}", font=Font, fill=(0,0,0))
        y_text += line_height
    except:
        bot.send_message(message.chat.id, "Error No URL is passed")
    else:    
        Font = ImageFont.truetype('Roboto[wdth,wght].ttf', size = 40)
        for text in handle_text_doc.splitted[0]:
            lines = textwrap.wrap(text, width=100)
            for line in lines:
                if (y_text + line_height < 1080):
                    line_width, line_height = Font.getsize(line)
                    draw.text(((1920 - line_width) / 2, y_text), line, font=Font, fill=(0,0,0))
                    y_text += line_height
                else :
                    img2 = Image.new('RGB', (1920, 1080), color='white')
                    draw2 = ImageDraw.Draw(img2)
                    y_text2 = 10
                    line_width2, line_height2 = Font.getsize(line)
                    draw2.text(((1920 - line_width2) / 2, y_text2), line, font=Font, fill=(0,0,0))
                    y_text2 += line_height2
                    img_exist = True
        
        file_name = time.strftime("%Y%m%d-%H%M%S") + ".png"
        img.save(file_name)
        bot.send_message(message.chat.id, "File processing completed")
        bot.send_photo(message.chat.id, photo=open(file_name,'rb'))
        os.remove(file_name)
        if (img_exist):
            file_name = time.strftime("%Y%m%d-%H%M%S") + ".png"
            img2.save(file_name)
            bot.send_photo(message.chat.id, photo=open(file_name,'rb'))
            os.remove(file_name)

@bot.message_handler(func= lambda message: message.text == 'None')
def exportNone(message):
    """If user does not want to export the summary in any format.

    Args:
        message (object)
    """
    bot.send_message(message.chat.id,"Thank You for using this bot")

@bot.message_handler(commands=['start','help','Start','Help','START','HELP'])
def greet(message):
    """Greets the first time user.

    Args:
        message (object)
    """
    greet = (f"Hello {message.from_user.username},\nWikipedia Summarizer Bot this side.\nHere you can send" +
            " link of any wikipedia article to summarize it.\nThis bot is created by Gurman Singh.\nThank You for using it")
    bot.send_message(message.chat.id, greet)

@bot.message_handler(regexp="(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?")
def handle_text_doc(message):
    """Received message is checked, whether it contains a url or not and then further 
        processed

    Args:
        message (object)
    """
    try:
        url = re.search("(?P<url>https?://[^\s]+)", message.text).group("url")
        print(url)
    except :
        print("Error reading url")
    else:
        if (valid_site(url)):
            handle_text_doc.splitted = telebot.util.split_string(generate_summary(url,3),3000)
            handle_text_doc.title = get_title(url)
            bot.send_message(message.chat.id, f"Summary of {handle_text_doc.title}:")

            for text in handle_text_doc.splitted[0]:
                print(text)
                bot.send_message(message.chat.id, text)

            export_summary(message)
        else:
            bot.send_message(message.chat.id, "Your Link is broken please check it")

@bot.message_handler(func = lambda message: True, 
                        content_types=['audio','photo','voice','video','document','contact','text','location','sticker'])
def default_message(message):
    """All the other messages that does not contain url are received here

    Args:
        message (object)
    """
    bot.send_message(message.chat.id, "Command Not recognised")

# let's begin
if __name__ == "__main__":
    while(True):
        try:
            bot.polling()
        except:
            continue
