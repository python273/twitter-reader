# twitter-reader

Read *full* X/Twitter threads in a threaded UI.

A random thread to check out the reader:
https://tw.cns.wtf/#1559672719414681601

```
$ python3 load_thread_async.py 12345 threads/thread_12345.json
$ python3 thread_to_tree_grouped.py threads/thread_12345.json app/public/tree_12345.json
$ cd app
$ npm run dev

$ open "http://localhost:5000/#12345"
```

```
# Runs the same steps
$ sh load.sh 12345
```
