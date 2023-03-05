# twitter-reader

Twitter thread reader that shows tweets as comments tree **(WIP)**

A random thread to check out the reader:
https://tw.cns.wtf/#1559672719414681601

```
$ python3 load_thread_async.py 12345
$ python3 thread_to_tree_grouped.py 12345
$ mv tree_12345.json app/public/
$ cd app
$ npm run dev

$ open "http://localhost:5000/#12345"
```

```
# Runs the same steps
$ sh load.sh 12345
```
