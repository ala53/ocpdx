import compiler
import os
def compile(compiler):
    compiler.set_input_dir("../site")
    compiler.set_output_dir("../minified")
    template = compiler.template("template.html")
    compiler.load_and_copy_css(minify = True)
    compiler.load_and_copy_js(minify = True)
    compiler.copy_images(minify = True) # Compresses images and copy
    compiler.copy_unknown_files() # Copies all files that don't end in .js, .css, .png, .jpg, or .html
    # And map all the HTML files
    # Files that don't need special treatment
    simple_files = [ 
        #404 page generated separately
        ["Yearly Barbecue", "barbecue.html"],
        ["Contact Us", "contact.html"],
        ["Donate", "donate.html"],
        ["Fundraising", "fundraising.html"],
        ["Home", "index.html"],
        ["Meeting Information", "meetings.html"],
        ["News Editor", "news_editor.html"], #To actually be implemented...
        ["Upcoming Events", "upcoming.html"]
    ]
    for files in simple_files:
        template.copy().inject("title", files[0]).inject("content", compiler.template(files[1])).save(files[1], True)
    # Files that need some TLC
    #Copy the 404 page to both /minified and /<root>
    template.copy().inject("title", "404 Not Found").inject("content", compiler.template("404.html")).save("404.html").save("../404.html")

    #And handle news sections
    compile_news_articles(template, compiler)

def compile_news_articles(template, compiler):
    article_files = []
    article_path = os.path.abspath("../site/news/articles")
    for f in os.listdir(article_path):
        fpath = os.path.join(article_path, f)
        if os.path.isfile(fpath): article_files.append(f)
    #Sort reverse alphabetically 
    article_files_chosen = sorted(article_files, reverse = True)
    #lines[0] and lines[1] are title and date, respectively
    article_infos = []
    #Read the files and build the templates
    for file in article_files_chosen:
        f = open(os.path.join(article_path, file), "r")
        data = str(f.read())
        lines = data.splitlines(False)
        title = lines[0]
        date = lines[1]
        text = "\n".join(lines[2:])
        article_infos.append(compiler.template("news/news_template.html").inject("title", title).inject("date", date).inject("content", text))
    #Build the news page template
    #Only put the last 20 in the news
    template.copy().inject("title", "News").inject("content", compiler.template("news.html").inject("articles", article_infos[0:20])).save("news.html")
    #But have an archive with all of them
    template.copy().inject("title", "News").inject("content", compiler.template("news_archive.html").inject("articles", article_infos[21:])).save("news_archive.html")
compile(compiler.Compiler())