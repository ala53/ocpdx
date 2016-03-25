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
    img = Image.open(fileObj.fullPath)
    img.save(outFile, quality = 80, optimize = True)
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
if not "$$content$$" in htmlTemplate:
    print("Global template is missing $$content$$ marker")
    sys.exit(-1)

#Where to output to
outPath = os.path.abspath(sys.argv[2])

#Clean out and recreate if it exists
try:
    #if os.path.exists(outPath): shutil.rmtree(outPath)
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
        print("Minifying CSS in " + arg.fullPath)
    elif fileExt == ".js":
        jsToRead[arg.fullPath] = Minifiable(readTextFile(arg.fullPath), arg)
        print("Minifying JS in " + arg.fullPath)
    elif fileExt == ".html" or fileExt == ".htm":
        text = str(readTextFile(arg.fullPath))
        #Check if it should be injected into template or if it is standalone
        if not text.startswith("<!--NOTEMPLATE-->"): text = str(htmlTemplate).replace("$$content$$", text)
        htmlToRead[arg.fullPath] = Minifiable(text, arg)
        print("Minifying HTML for " + arg.fullPath)
    elif fileExt == ".png":
        #Compress the (transparent) image
        compressImage(outPath, arg)
        print("Compressed and copied " + arg.fullPath)        
    elif fileExt == ".jpg" or fileExt == ".jpeg":
        #Compress the image
        compressImage(outPath, arg)
        print("Compressed and copied " + arg.fullPath)
    else:
        copyBinaryFile(outPath, arg)
        print("Copied " + arg.fullPath)

for minifiable in cssToRead.values():
    #Minify the css
    minifiable.data = compress(minifiable.data)
    
for minifiable in jsToRead.values():
    #Minify the js
    minifiable.data = jsmin(minifiable.data)

for minifiable in htmlToRead.values():
    print()
    print("Processing " + minifiable.fileInfo.fullPath)
    #Parse it and replace css with inline if length < 15000 (~15kb)
    parser = BeautifulSoup(minifiable.data, "html.parser")
    for js in parser.find_all("script"):
        scriptFile = js.get("src")
        if scriptFile == None: 
            #It's inline so just minify inline
            js.string = jsmin(js.string)
            continue 
        resolved = os.path.abspath(os.path.join(minifiable.fileInfo.dir, scriptFile))
        if not resolved in jsToRead: 
            print("\t -> JS file not found: " + resolved + ", ignoring b/c probably not local file")
            continue
        resolvedJs = jsToRead[resolved]
        if len(resolvedJs.data) > 15000: 
            print("\t -> Not inlining " + resolved + ". Reason: too large")
            continue
        print("\t -> [Inlined] JS File: " + scriptFile + " resolved as " + resolved)
        #Remove the src tag
        js['src'] = ""
        js.string = resolvedJs.data # + " /*JS from " + resolvedJs.fileInfo.fullPath + "*/"
        
        
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
        if len(resolvedCss.data) > 15000: 
            print("\t -> Not inlining " + resolved + ". Reason: too large")
            continue
        print("\t -> [Inlined] CSS File: " + scriptFile + " resolved as " + resolved)
        #Switch from link to style
        css['href'] = ""
        css.name = "style"
        css['rel'] = ""
        css['type'] = ""
        css.string = resolvedCss.data
    minifiable.inlined = str(parser)  
    mf = Minifier(True, True, True, True, True, True, True)
    minifiable.data = mf.minify(minifiable.inlined)   

for f in cssToRead.values(): writeFile(f, outPath)
for f in jsToRead.values(): writeFile(f, outPath)
for f in htmlToRead.values(): writeFile(f, outPath)

print("Compiled to " + outPath)