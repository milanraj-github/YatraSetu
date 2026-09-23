import base64

# A small 48x48 Google 'G' logo PNG (transparent background)
# (Using a generic small blue square as placeholder just to make it valid if I can't find the real one, but let's try to get a valid PNG)
import urllib.request
url = "https://raw.githubusercontent.com/flutter/flutter/master/packages/flutter_tools/templates/app/android.tmpl/app/src/main/res/mipmap-hdpi/ic_launcher.png"
# wait, I can just grab one from a CDN
req = urllib.request.Request("https://cdn1.iconfinder.com/data/icons/google-s-logo/150/Google_Icons-09-512.png", headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    with open("frontend/assets/images/google_logo.png", "wb") as f:
        f.write(response.read())
