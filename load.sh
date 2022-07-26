python3 load_thread.py $1
python3 thread_to_tree_grouped.py $1
mv tree_$1.json app/public/
open "http://localhost:5000/#$1"
