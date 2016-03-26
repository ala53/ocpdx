

import sys
import os

if len(sys.argv[1:]) < 2:
    print("This module publishes a new news object and recompiles the website")
    print("Expects first argument to be the news HTML file to publish and the second to be the title of the article")
    print("Missing an argument!")
    sys.exit(-1)
    
import time

pretty_time = time.strftime("%m/%d/%Y %I:%M %p")
tfile = open(sys.argv[1], "r")
text_to_pub = str(tfile.read())
tfile.close()
title = str(sys.argv[2])

location = os.path.abspath("../site/news/articles")
id = len(os.listdir(location)) + 1

file = open(os.path.join(location, str(id) + ".html"), "wb")

text = title + "\n" + pretty_time + "\n" + text_to_pub

file.write(text.encode("utf8", "ignore"))

file.flush()
file.close()

print("published")