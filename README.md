# MRJAN server

Bu papkadagi main.py — foydalanuvchi yuborgan oxirgi main.py.

APK bu Flask saytini WebView ichida ochadi:
http://10.44.237.53:5000

Agar Flask HTML ichiga rasm qo'shilsa, rasmni Flask static papkasiga joylash kerak:
server/static/images/

Masalan:
server/static/images/logo.png

HTML ichida:
<img src="/static/images/logo.png">

Hozirgi main.py'da alohida rasm fayllari ko'rsatilmagan; mavjud dizayn HTML/CSS asosida.
