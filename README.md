# twitter-reader

Read *full* X/Twitter threads in a threaded UI.

A random thread to check out the reader:
https://tw.cns.wtf/#1559672719414681601

```
# Server for local usage
$ python3 server_thread_loader.py
$ cd app
$ npm run dev
```

Then open `http://localhost:3412/` and paste tweet URL.

Or use `twitter-reader.userscript.js` userscript (e.g. via Violentmonkey addon), it adds buttons in top right corner of tweets, and click `Thread`.

In the reader, `[message focus]+Shift+H` opens the focused tweet through the local loader.

---

Manual via term options:

```
$ python3 load_thread_async.py 12345 app/public/tree_12345.json
$ cd app
$ npm run dev

$ open "http://localhost:5000/#12345"
```

```
# Runs the same steps
$ sh load.sh 12345
```
