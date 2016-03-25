#Configuration settings
maxInliningTextSize = 15000 #Set to 0 to disable inlining, default = 15000
shouldMinify = True

import os
import sys
import shutil
#PNG compressor
from PIL import Image

# Add the current directory to PATH so we can load the local packages
compilerDir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(compilerDir)

#Import HTML parser
from bs4 import BeautifulSoup
#Import CSS compressor
from csscompressor import compress
#Import HTML minifier
from htmlmin import Minifier
#Import JS parser
from jsmin import jsmin

class Minifiable:
    def __init__(self, data, fileInfo):
        self.data = data
        self.fileInfo = fileInfo

class FilenameObject:
    def __init__(self, basePath, subPath, filename, fullName, fullDir):
        self.basePath = basePath
        self.subPath = subPath
        self.filename = filename
        self.fullPath = fullName
        self.dir = fullDir

def readTextFile(filename):
    f = open(filename, encoding= "utf8")
    data = f.read()
    f.close()
    return data

def copyBinaryFile(outRoot, fileObj):
    outPath = os.path.join(outRoot, fileObj.subPath)
    outFile = os.path.join(outPath, fileObj.filename)
    if not os.path.exists(outPath): os.mkdir(outPath)
    shutil.copyfile(fileObj.fullPath, outFile)

def compressImage(outRoot, fileObj):
    outPath = os.path.join(outRoot, fileObj.subPath)
    outFile = os.path.join(outPath, fileObj.filename)
    if not os.path.exists(outPath): os.mkdir(outPath)
    img = Image.open(fileObj.fullPath)
    img.save(outFile, quality = 80, optimize = True)
    img.close()
    
def writeFile(minifiable, outRoot, data = None):
    if data == None: data = minifiable.data
    fileObj = minifiable.fileInfo
    outFile = os.path.join(outRoot, fileObj.subPath, fileObj.filename)
    outPath = os.path.join(outRoot, fileObj.subPath)
    if not os.path.exists(outPath): os.mkdir(outPath)
    f = open(outFile, "wb")
    f.write(str(data).encode("utf8", "ignore"))
    f.flush()
    f.close()

#Args[0] = compile.py
#Args[1] = Output
#Args[2] = Input 1
#Args... = Input n

if len(sys.argv) < 4:
    print("Missing argument(s)!")
    print("\tExpected: python compile.py template_file output_directory input_directory_1 [in_dir2] [in_dir3] ...")
    sys.exit(-1)

#The global template
htmlTemplate = readTextFile(sys.argv[1])
htmlTemplateFile = os.path.abspath(sys.argv[1])
if not "$$content$$" in htmlTemplate:
    print("Global template is missing $$content$$ marker")
    sys.exit(-1)
if not "$$title$$" in htmlTemplate:
    print("Global template is missing $$title$$ marker(s)")
    sys.exit(-1)

def injectIntoTemplate(text):
    #If it doesn't want to be templated
    if text.startswith("<!--NOTEMPLATE-->"): return text
    text = str(text)
    template = str(htmlTemplate)
    #Tries to inject the specified data into the htmlTemplate
    if text.startswith("$$title$$"):
        #it has a title we need to extract first
        asLines = text.splitlines(False)
        titleLine = asLines[0]
        #Skip the "$$title$$" part of the line
        title = titleLine[len("$$title$$ "):]
        template = template.replace("$$title$$", title)
        #And put all the other lines back in order
        text = "\n".join(asLines[1:])
    else: template = template.replace("$$title$$", "") #No title, so just ignore iter
    #and inject the content
    template = template.replace("$$content$$", text)
    return template

#Where to output to
outPath = os.path.abspath(sys.argv[2])

#Clean out and recreate if it exists
try:
    if os.path.exists(outPath): shutil.rmtree(outPath)
    if not os.path.exists(outPath): os.mkdir(outPath)
except: pass

#Get all the filenames in this directory tree
filenamesToScan = []
for path in sys.argv[3:]:
    path = os.path.abspath(path)
    for spath, subdirs, files in os.walk(path):
        for name in files:
            fullPath = os.path.join(spath, name)
            #Strip the base path from full path
            subPath = str(spath).replace(path, "")
            if subPath.startswith("\\") or subPath.startswith("/"): subPath = subPath[1:]
            filenamesToScan.append(FilenameObject(spath, subPath, name, fullPath, spath))

htmlToRead = dict()
cssToRead = dict()
jsToRead = dict()
for arg in filenamesToScan:
    filePath, fileExt = os.path.splitext(arg.fullPath)
    fileExt = fileExt.lower()
    if fileExt == ".css":
        cssToRead[arg.fullPath] = Minifiable(readTextFile(arg.fullPath), arg)
        print("Found CSS in " + arg.fullPath)
    elif fileExt == ".js":
        jsToRead[arg.fullPath] = Minifiable(readTextFile(arg.fullPath), arg)
        print("Found JS in " + arg.fullPath)
    elif fileExt == ".html" or fileExt == ".htm":
        #Ignore the template file if this is it
        if htmlTemplateFile == arg.fullPath:
            print("Ignoring template file (" + arg.fullPath + ")")
            continue
        text = str(readTextFile(arg.fullPath))
        text = injectIntoTemplate(text)
        htmlToRead[arg.fullPath] = Minifiable(text, arg)
        print("Found HTML for " + arg.fullPath)
    elif fileExt == ".png" or fileExt == ".jpg" or fileExt == ".jpeg":
        #Compress the image
        if shouldMinify: 
            compressImage(outPath, arg)
            print("Compressed and copied " + arg.fullPath)
        else: 
            copyBinaryFile(outPath, arg)
            print("Copied " + arg.fullPath)
    else:
        copyBinaryFile(outPath, arg)
        print("Copied " + arg.fullPath)

for minifiable in cssToRead.values():
    #Minify the css
    if shouldMinify:
        minifiable.data = compress(minifiable.data, 0, False)
        print("Minified CSS in " + minifiable.fileInfo.fullPath)
    
for minifiable in jsToRead.values():
    #Minify the js
    if shouldMinify:
        minifiable.data = jsmin(minifiable.data)
        print("Minified JS in " + minifiable.fileInfo.fullPath)

for minifiable in htmlToRead.values():
    print()
    print("Processing " + minifiable.fileInfo.fullPath)
    #Parse it and replace css with inline if length < 15000 (~15kb)
    parser = BeautifulSoup(minifiable.data, "html.parser")
    for js in parser.find_all("script"):
        scriptFile = js.get("src")
        if scriptFile == None: 
            #It's inline so just minify inline
            if shouldMinify: js.string = jsmin(js.string)
            continue 
        resolved = os.path.abspath(os.path.join(minifiable.fileInfo.dir, scriptFile))
        if not resolved in jsToRead: 
            print("\t -> JS file not found: " + resolved + ", ignoring b/c probably not local file")
            continue
        resolvedJs = jsToRead[resolved]
        if len(resolvedJs.data) > maxInliningTextSize: 
            print("\t -> Not inlining " + resolved + ". Reason: too large")
            continue
        print("\t -> [Inlined] JS File: " + scriptFile + " resolved as " + resolved)
        #Remove the src tag
        js.attrs['src'] = None
        js.string = resolvedJs.data # + " /*JS from " + resolvedJs.fileInfo.fullPath + "*/"
        
        
    #handle inline <style> tags
    for css in parser.find_all("style"):
        if shouldMinify: css.string = compress(css.string, 0, False)
     
    #And external ones   
    for css in parser.find_all("link"):
        scriptFile = css.get("href")
        if css.get('rel') != ["stylesheet"]: 
            print("<link> is not stylesheet, is " + str(css.get('rel')))
            continue #Not a CSS link
        if scriptFile == None: continue #It's an inline scriptFile
        resolved = os.path.abspath(os.path.join(minifiable.fileInfo.dir, scriptFile))
        if not resolved in cssToRead: 
            print("\t -> CSS file not found: " + resolved + ", ignoring b/c probably not local file")
            continue
        resolvedCss = cssToRead[resolved]
        if len(resolvedCss.data) > maxInliningTextSize: 
            print("\t -> Not inlining " + resolved + ". Reason: too large")
            continue
        print("\t -> [Inlined] CSS File: " + scriptFile + " resolved as " + resolved)
        #Switch from link to style
        css.attrs['href'] = None
        css.name = "style"
        css.attrs['rel'] = None
        css.attrs['type'] = None
        css.string = resolvedCss.data
    
    #Finally, inline and minify the HTML
    minifiable.inlined = str(parser)  
    if shouldMinify:
        mf = Minifier(True, True, True, True, True, True, True)
        minifiable.data = mf.minify(minifiable.inlined)   
        print("Minified HTML in " + minifiable.fileInfo.fullPath)
    else: minifiable.data = minifiable.inlined

for f in cssToRead.values(): writeFile(f, outPath)
for f in jsToRead.values(): writeFile(f, outPath)
for f in htmlToRead.values(): writeFile(f, outPath)

print("Compiled to " + outPath)
if not shouldMinify: print("[WARNING] Minification was disabled, do not use in production")
if maxInliningTextSize == 0: print("[WARNING] JS/CSS inlining was disabled, do not use in production")