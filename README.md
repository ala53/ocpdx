# ocpdx.org
The website for the Northeast Portland Optimist Club. 

## Building
Requires Windows and Pillow (Python Image Processing Library).
 - Just run `compiler/compile.cmd` to build the site from the sources.
 - `compile.py` is the site specific compiler, which processes the site data. To add a new page, make a change there.
 - `compiler.py` is a simple template compiler. It inlines CSS and JS into the HTML to avoid extra page loads (we don't all have HTTP/2.0), handles image minification, and minifies the output HTML of the website. There's also a really simple template system.
   - Create a new compiler object with `Compiler()`.
   - Set input directory with `compiler.set_input_dir()`
   - Set output directory with `compiler.set_output_dir()`
   - Search for files with `compiler.get_files()`
   - Copy CSS, JS, images, and other files with `compiler.load_and_copy_css()`, `compiler.load_and_copy_js()`, `compiler.copy_images()`, `compiler.copy_unknown_files()`.
   - Load templates with `compiler.template(filename)`
     - Inject either strings or other template objects with `template.inject(block_name, data_to_inject)`
     - Save with `template.save(filename)`
     - A template block is just something in the HTML file with a `$$` surrounding it. E.g. `<title>$$title$$</title>`. If you call `template.inject("title", "Page Title")`, the output will be `<title>$$title$$</title>`. If the `inject` call is not executed, the block will be replaced with an empty string. E.g. `<title></title>`. 
