from .modes.diary_mode import add_entry
from .modes.teaching_mode import add_fact, add_snippet
from .modes.chat_mode import chat, ChatLockedError
from .logic.coder import generate_code
from .logic.importer import process_file
from .logic.asker import get_answer
from .logic.converse import get_reply
from .logic.notes import add_note, search_notes
from .logic.todo import add_task, list_tasks, mark_done
from .logic.recall import search as recall_search
from datetime import datetime
from .utils.datetime import request_timestamp
from .config import ENABLE_TIMESTAMP_REQUEST, ENABLE_TAGGING
from .utils.voice import speak, recognize_speech

HELP_TEXT = """Commands:
/mode diary   - enter diary mode
/mode teach   - enter teaching mode
/mode chat    - chat with Solace (requires 10 diary entries)
/note <text>  - save a short note
/todo ...     - manage tasks (add/list/done)
/ask <q>      - search notes and diary
/code <task>  - generate a code snippet
/import <f>   - import facts from file
/chat <msg>   - quick conversation
/speak [txt]  - say text aloud
/listen       - listen and process speech
/help         - show this message
/exit         - exit program
"""


def main():
    current_mode = 'diary'
    print('Welcome to Solace. Type /help for commands.')

    def _timestamp():
        if ENABLE_TIMESTAMP_REQUEST:
            return request_timestamp()
        return datetime.now().strftime('%Y-%m-%d %H:%M')

    def _tag_prompt():
        tags = []
        important = False
        if ENABLE_TAGGING:
            resp = input('Would you like to mark this as important or tag it for easy search later? [y/N]: ').strip().lower()
            if resp.startswith('y'):
                tag_line = input('Enter tags separated by space (optional): ').strip()
                if tag_line:
                    tags = tag_line.split()
                imp = input('Mark as important? [y/N]: ').strip().lower()
                if imp.startswith('y'):
                    important = True
        return tags, important

    while True:
        try:
            line = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line.startswith('/mode'):
            parts = line.split()
            if len(parts) >= 2:
                current_mode = parts[1]
                print(f'Mode set to {current_mode}')
            else:
                print('Usage: /mode <diary|teach|chat>')
            continue
        if line.startswith('/help'):
            print(HELP_TEXT)
            continue
        if line.startswith('/exit'):
            break
        if line.startswith('/import'):
            _, path = line.split(maxsplit=1)
            count = process_file(path)
            print(f'Imported {count} facts.')
            continue
        if line.startswith('/note'):
            note_text = line[len('/note'):].strip()
            ts = _timestamp()
            tags, imp = _tag_prompt()
            add_note(note_text, ts, tags, imp)
            print('Note saved.')
            continue
        if line.startswith('/todo'):
            parts = line.split(maxsplit=2)
            if len(parts) >= 2:
                cmd = parts[1]
            else:
                cmd = ''
            if cmd == 'add' and len(parts) == 3:
                task_text = parts[2]
                ts = _timestamp()
                tags, imp = _tag_prompt()
                item = add_task(task_text, ts, tags, imp)
                print(f"Task {item['id']} added.")
            elif cmd == 'list':
                tasks = list_tasks()
                for t in tasks:
                    mark = 'x' if t['done'] else ' '
                    print(f"[{mark}] {t['id']}: {t['task']}")
            elif cmd == 'done' and len(parts) == 3:
                try:
                    tid = int(parts[2])
                except ValueError:
                    print('Invalid task id')
                else:
                    if mark_done(tid):
                        print('Task marked done.')
                    else:
                        print('Task not found.')
            else:
                print('Usage: /todo add <task> | /todo list | /todo done <id>')
            continue
        if line.startswith('/ask'):
            query = line[len('/ask'):].strip()
            results = recall_search(query)
            for r in results:
                ts = r.get('timestamp', '')
                print(f"[{ts}] {r.get('text', '')}")
            if not results:
                response = get_answer(query)
                print(response)
                speak(response)
            continue
        if line.startswith('/code'):
            task = line[len('/code'):].strip()
            print(generate_code(task))
            continue
        if line.startswith('/chat'):
            message = line[len('/chat'):].strip()
            response = get_reply(message)
            print(response)
            speak(response)
            continue
        if line.startswith('/speak'):
            text = line[len('/speak'):].strip()
            if text:
                speak(text)
            continue
        if line.startswith('/listen'):
            try:
                heard = recognize_speech()
            except Exception as e:
                print(f'Error: {e}')
                continue
            if not heard:
                print('Sorry, I did not catch that.')
                continue
            print(f'You said: {heard}')
            if heard.endswith('?'):
                resp = get_answer(heard)
            else:
                resp = get_reply(heard)
            print(resp)
            speak(resp)
            continue

        if current_mode == 'diary':
            ts = _timestamp()
            tags, imp = _tag_prompt()
            mood = add_entry(line, ts, tags, imp)
            print(f'Entry saved. Detected mood: {mood}')
        elif current_mode == 'teach':
            if ':' in line:
                key, value = line.split(':', 1)
                add_fact(key.strip(), value.strip())
                print('Fact stored')
            elif line.startswith('snippet '):
                parts = line.split(None, 2)
                if len(parts) == 3:
                    key = parts[1]
                    code = parts[2]
                    add_snippet(key, code)
                    print('Snippet stored')
            else:
                print('Use "<fact>: <value>" or "snippet <key> <code>"')
        elif current_mode == 'chat':
            try:
                print(chat(line))
            except ChatLockedError as e:
                print(e)
        else:
            print('Unknown mode')

    print('Goodbye!')


if __name__ == '__main__':
    main()
