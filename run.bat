start cmd /k "npx parcel index.html"
start cmd /k "python src/main.py"
timeout /t 2 /nobreak
.\node_modules\.bin\electron .