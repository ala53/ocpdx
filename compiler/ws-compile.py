import compiler
def compile(c):
    c.set_input_dir("../site")
    c.set_output_dir("../minified")
    template = c.template("template.html")
    c.load_and_copy_css(minify = True)
    c.load_and_copy_js(minify = True)
    c.copy_images(minify = True)
    c.copy_unknown_files()
    # And map all the HTML files
    # Files that don't need special treatment
    simple_files = [ 
        ["Yearly Barbecue", "barbecue.html"],
        ["Contact Us", "contact.html"],
        ["Donate", "donate.html"],
        ["Essay Contest", "essay.html"],
        ["Home", "index.html"],
        ["Meeting Information", "meetings.html"],
        ["News", "news.html"],
        ["News Editor", "news_editor.html"],
        ["Oratorical Contest", "oratorical.html"],
        ["Upcoming Events", "upcoming.html"]
    ]
    for files in simple_files:
        template.copy().inject("title", files[0]).inject("content", c.template(files[1])).save(files[1], True)
    # Files that need some TLC
    #Copy the 404 page to both /minified and /<root>
    template.copy().inject("title", "404 Not Found").inject("content", c.template("404.html")).save("404.html").save("../404.html")
  

compile(compiler.Compiler())