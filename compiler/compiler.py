import shutil
import os
import sys
import enum
import copy

#Import image compressor
from PIL import Image
#Import HTML parser
from bs4 import BeautifulSoup
#Import CSS compressor
from csscompressor import compress as csscompress
#Import HTML minifier
from htmlmin import Minifier
#Import JS parser
from jsmin import jsmin
# Add the current directory to PATH so we can load the local packages
compilerDir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(compilerDir)

class _TemplateBlock:
    def __init__(self, name, preamble):
        self.name = name
        self.preamble = preamble
    def __str__(self, **kwargs):
        return "---->>>" + self.name + "<-----\n\t\t" + self.preamble

def _loadTemplate(filename):
    """Loads the template and gets a list of all the 'block' names in it"""
    f = open(filename, "r")
    rawHtml = str(f.read())
    f.close()
    
    blocks = dict()
    block_names = set()
    # Read character by character looking for $$XX$$ expressions
    last_block_end_char = 0
    is_in_block = False
    block_start = 0
    i = 0
    while i < len(rawHtml) - 1:
        if is_in_block:
            # Search for the block's end
            if rawHtml[i] == "$" and rawHtml[i + 1] == "$":
                i += 2 # Move the cursor to the end of the block
                is_in_block = False
                name = rawHtml[block_start : (i - 2)] # Get the name
                # Mark the name of the block and get the text
                blocks[name] = _TemplateBlock(name, rawHtml[last_block_end_char : (block_start - 2)])
                last_block_end_char = i # Mark the end of the block
                block_names.add("$$" + name + "$$")
        # Look for the beginning of the block
        if rawHtml[i] == "$" and rawHtml[i + 1] == "$":
            is_in_block = True
            i += 2
            block_start = i
            continue
        #Otherwise, keep moving
        i += 1
    if is_in_block: 
        print("WARN! UNCLOSED BLOCK in " + filename)
        l, o = _calc_line(rawHtml, block_start)
        print("line " + str(l) + " offset " + str(o))
        sys.exit()
    # And add the end-of-html block
    blocks["__END__"] = _TemplateBlock("__END__", rawHtml[last_block_end_char:])
    return (rawHtml, block_names)

def _calc_line(data, offset):
    linecount = 1
    off = 1
    curroff = 0
    for c in data:
        off += 1
        curroff += 1
        if c == "\n":
            off = 1
            linecount += 1
        if curroff == offset: return (linecount, off)

class FileType(enum.Enum):
    html = 0
    css = 1
    js = 2
    png = 3
    jpg = 4
    other = 5

class LiteralFilePath:
    def __init__(self, filename, base=None):
        filename = str(os.path.abspath(filename))
        if not base == None: base = str(os.path.abspath(base))
        else: base = ""
        head, tail = os.path.split(filename)
        self.full_path = filename
        self.filename = tail
        self.dir = head
        self.base_path = base
        self.base_relative = self.full_path.replace(base, "")
        # Cut off the beginning slash
        if self.base_relative.startswith("\\") or self.base_relative.startswith("/"):
            self.base_relative = self.base_relative[1:]
        self.base_relative_dir = self.dir.replace(base, "")
        # Cut off the beginning slash
        if self.base_relative_dir.startswith("\\") or self.base_relative_dir.startswith("/"):
            self.base_relative_dir = self.base_relative_dir[1:]
class FileObject:
    def __init__(self, type, filename, compiler):
        self.type = type
        self.input = LiteralFilePath(filename, compiler.in_path)
        fname = filename.replace(compiler.in_path, compiler.out_path)
        self.output = LiteralFilePath(fname, compiler.out_path)
        self.base_path = compiler.out_path
    def copy_to_output(self):
        """Copies the file exactly to the output directory"""
        self.ensure_dirs_exist()
        shutil.copyfile(self.input.full_path, self.output.full_path)
        pass
    def get_filename(self):
        """Gets the filename that this object represents"""
        return self.input.full_path
    def get_output_filename(self):
        """Gets the filename that this file should be saved to"""
        return self.output.full_path
    def ensure_dirs_exist(self):
        if not os.path.exists(self.output.dir): os.makedirs(self.output.dir)
    def read_as_binary(self):
        """Reads the file as a bytes() object"""
        f = open(self.input.full_path, "rb")
        data = f.read()
        f.close()
        return bytes(data)
    def read_as_string(self):
        """Reads the file as a string"""
        f = open(self.input.full_path, "r")
        data = f.read()
        f.close()
        return str(data)
    def write_to_output(self, data):
        """Writes the specified data (string or bytes() object) to the output file"""
        if isinstance(data, str): data = data.encode("utf8", "ignore")
        self.ensure_dirs_exist()
        f = open(self.output.full_path, "wb")
        f.write(data)
        f.flush()
        f.close()

class Compiler:
    def __init__(self):
        self.js_cache = dict()
        self.css_cache = dict()
    def set_output_dir(self, dir):
        """Sets the directory to output files to"""
        self.out_path = str(os.path.abspath(dir))
    def set_input_dir(self, dir):
        """Sets the directory to read files from"""
        self.in_path = str(os.path.abspath(dir))
    def _resolve_input_filename(self, name):
        if os.path.isabs(name): return name
        return os.path.abspath(os.path.join(self.in_path, name))
    def _resolve_output_filename(self, name):
        if os.path.isabs(name): return name
        return os.path.abspath(os.path.join(self.out_path, name))
    def get_files(self):
        """Finds all the files in the input directory and maps them to their output filenames"""
        file_set = []
        for spath, subdirs, files in os.walk(self.in_path):
            for name in files:
                fullPath = os.path.join(spath, name)
                p, ext = os.path.splitext(fullPath)
                ext = str(ext).lower()
                if ext == ".css":
                    file_set.append(FileObject(FileType.css, fullPath, self))
                elif ext == ".js":
                    file_set.append(FileObject(FileType.js, fullPath, self))
                elif ext == ".htm" or ext == ".html":
                    file_set.append(FileObject(FileType.html, fullPath, self))
                elif ext == ".jpg" or ext == ".jpeg":
                    file_set.append(FileObject(FileType.jpg, fullPath, self))
                elif ext == ".png":
                    file_set.append(FileObject(FileType.png, fullPath, self))
                else:
                    file_set.append(FileObject(FileType.other, fullPath, self))

        return file_set
    def load_and_copy_css(self, minify=True):
        """Loads the CSS files, minifies them if requested, and copies them to the output directory"""
        files = self.get_files()
        for file in files:
            if file.type == FileType.css:
                css = file.read_as_string()
                if minify: css = csscompress(css, 0, False)
                file.write_to_output(css) # Save it to output dir
                self.css_cache[file.get_filename()] = css # And cache it
    def load_and_copy_js(self, minify=True):
        """Loads the JS files, minifies them if requested, and copies them to the output directory"""
        files = self.get_files()
        for file in files:
            if file.type == FileType.js:
                js = file.read_as_string()
                if minify: js = jsmin(js)
                file.write_to_output(js) # Save it to output dir
                self.js_cache[file.get_filename()] = js # And cache it
    def copy_images(self, minify=True):
        """Loads the images (png, jpg), compresses them if requested, and copies to output directory"""
        files = self.get_files()
        for file in files:
            if file.type == FileType.png or file.type == FileType.jpg:
                if not minify:
                    file.copy_to_output()
                    continue
                img = Image.open(file.get_filename())
                file.ensure_dirs_exist()
                img.save(file.get_output_filename(), quality = 80, optimize = True)
                img.close()
        return
    def copy_unknown_files(self):
        """Copies all files that could not be identified as html, images, css, or JS"""
        files = self.get_files()
        for file in files:
            if file.type == FileType.other:
                print("[Copy] " + file.output.full_path)
                file.copy_to_output()
    def template(self, filename):
        """Creates a template from the specified (relative) filename"""
        return Template(self, self._resolve_input_filename(filename))

class Template:
    def __init__(self, compiler, filename):
        self.compiler = compiler
        self.filename = filename
        html, blocks = _loadTemplate(filename)
        self._block_names = blocks
        self.rawHtml = html
        self.placeholders = dict()
        for block in blocks:
            self.placeholders[block] = "" # Fill in the blanks
        
        self.file_obj = FileObject(FileType.html, self.filename, self.compiler)
    def copy(self):
        """Copies this template instance so it can be reused"""
        return copy.deepcopy(self)
    def inject(self, name, data):
        """Injects the specified template, template list, or string into the placeholder from the original html (a $$PLACEHOLDER$$ block)"""
        if not name.startswith("$$"): name = "$$" + name
        if not name.endswith("$$"): name += "$$"
        if not name in self.placeholders: raise KeyError("No placeholder by name " + name)
        if not (isinstance(data, list) or isinstance(data, str) or isinstance(data, Template)): raise TypeError("Must be a template, string, or list thereof")
        self.placeholders[name] = data
        return self
    def __str__(self):
        text = self.rawHtml
        for block in self._block_names:
            content = self.placeholders[block]
            contentAsStr = ""
            if isinstance(content, list): #If it's a list, we need to stringify everything in it
                for it in content:
                    contentAsStr += str(it)
            else: contentAsStr = str(content)

            text = text.replace(block, contentAsStr)
        return text
    def save(self, filename, minify=True, inline=True):
        """Compiles and saves the HTML from this template, minifying and inlining styles and js if requested"""
        as_str = str(self)
        output_path = LiteralFilePath(os.path.abspath(os.path.join(self.compiler.out_path, filename)), self.compiler.out_path) 
        maxInliningTextSize = 15000
        # Disable inlining if necessary..
        if not inline: maxInliningTextSize = 0
        parser = BeautifulSoup(as_str, "html.parser")
        #If we should minify inline styles
        if minify:
            for css in parser.find_all("style"):
                if minify: css.string = csscompress(css.string, 0, False)
        # Look up external styles
        for css in parser.find_all("link"):
            file = css.get("href") # Get the path of the CSS
            #Check if it's a style sheet
            if css.get('rel') != ["stylesheet"]: 
                #print("<link> is not stylesheet, is " + str(css.get('rel')))
                continue #Not a CSS link
            #Resolve the path of the script file
            resolved = os.path.abspath(os.path.join(self.file_obj.input.dir, file))
            #Check if we know where the file is / if we cached it
            if not resolved in self.compiler.css_cache: 
                #print("\t -> CSS file not found: " + resolved + ", ignoring
                #b/c probably not local file")
                continue
            #Get the actual CSS data
            resolvedCss = self.compiler.css_cache[resolved]
            if len(resolvedCss) > maxInliningTextSize: 
                print("\t -> Not inlining " + resolved + ".  Reason: too large")
                continue
            #print("\t -> [Inlined] CSS File: " + scriptFile + " resolved as "
            #+ resolved)
            #Switch from link to style
            css.name = "style"
            #Clear attributes
            css.attrs['href'] = None
            css.attrs['rel'] = None
            css.attrs['type'] = None
            #And inject data
            css.string = resolvedCss

        #And handle JS file links
        for js in parser.find_all("script"):
            file = js.get("src")
            #Check if it is an inline script file
            if file == None: 
                if minify: js.string = jsmin(js.string)
                continue 
            resolved = os.path.abspath(os.path.join(self.file_obj.input.dir, file))
            #Check if we can resolve the file
            if not resolved in self.compiler.js_cache: 
                #print("\t -> JS file not found: " + resolved + ", ignoring b/c
                #probably not local file")
                continue
            resolvedJs = self.compiler.js_cache[resolved]
            #Check if it is inlinable
            if len(resolvedJs) > maxInliningTextSize: 
                print("\t -> Not inlining " + resolved + ".  Reason: too large")
                continue
            #print("\t -> [Inlined] JS File: " + scriptFile + " resolved as " +
            #resolved)
            #Remove the src tag
            js.attrs['src'] = None
            #And inject inline
            js.string = resolvedJs

        as_str = str(parser)
        #If we should minify...
        if minify: 
            minifier = Minifier(True, True, True, True, True, True, True)
            as_str = minifier.minify(as_str)

        #And save
        f = open(output_path.full_path, "wb")
        print("[Saved] " + output_path.full_path)
        f.write(as_str.encode("utf8", "ignore"))
        f.flush()
        f.close()
        return self