@echo off
echo "This will delete the entire folder of the compiled website."
echo "Are you sure?"
echo "Press CTRL+C to cancel or ENTER to continue"
pause

rmdir /S /Q "../minified"