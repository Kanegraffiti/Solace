from .modes.diary_mode import add_entry
from .modes.teaching_mode import add_fact, add_snippet
from .modes.chat_mode import chat, ChatLockedError
from .logic.codegen import lookup as code_lookup, explain as code_explain, add_example
from .logic.debugger import lookup as debug_lookup
from .logic.importer import process_file
from .logic.converse import get_reply
from .logic.notes import add_note
from .logic.todo import add_task, list_tasks, mark_complete, delete_task
from datetime import datetime
from .utils.datetime import request_timestamp
from .config import ENABLE_TIMESTAMP_REQUEST, ENABLE_TAGGING
from .utils.voice import speak, recognize_speech

HELP_TEXT = """Commands:
/mode diary   - enter diary mode
/mode teach   - enter teaching mode
/mode chat    - chat with Solace (requires 10 diary entries)
/notes        - create a note
/todo ...     - manage tasks (add/list/done/delete)
/ask <q>      - ask how to code something
/code <task>  - generate a code snippet
/debug <err>  - look up an error message
/teachcode    - add a coding example
/import <f>   - import facts from file
/teach upload <file> - import facts from supported file
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
        if line.startswith('/teach upload'):
            parts = line.split(maxsplit=2)
            if len(parts) == 3:
                filepath = parts[2]
                count = process_file(filepath)
                print(f'Imported {count} facts from {filepath}.')
            else:
                print('Usage: /teach upload <file>')
            continue
        if line.startswith('/notes'):
            title = input('Title: ').strip()
            date_in = input('Date (leave blank for now): ').strip()
            ts = date_in if date_in else _timestamp()
            tag_line = input('Tags (space separated, optional): ').strip()
            tags = tag_line.split() if tag_line else []
            content = input('Note content (end with blank line):\n')
            lines = []
            while True:
                ln = input()
                if not ln:
                    break
                lines.append(ln)
            text = '\n'.join([content] + lines).strip()
            enc = input('Encrypt? [y/N]: ').strip().lower().startswith('y')
            add_note(title, text, ts, tags, enc)
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
                item = add_task(task_text, ts)
                print(f"Added: {item['task']}")
            elif cmd == 'list':
                tasks = list_tasks()
                for i, t in enumerate(tasks):
                    mark = 'x' if t['status'] == 'complete' else ' '
                    print(f"[{mark}] {i}: {t['task']}")
            elif cmd == 'done' and len(parts) == 3:
                try:
                    idx = int(parts[2])
                except ValueError:
                    print('Invalid id')
                else:
                    if mark_complete(idx):
                        print('Task marked complete.')
                    else:
                        print('Task not found.')
            elif cmd == 'delete' and len(parts) == 3:
                try:
                    idx = int(parts[2])
                except ValueError:
                    print('Invalid id')
                else:
                    if delete_task(idx):
                        print('Task deleted.')
                    else:
                        print('Task not found.')
            else:
                print('Usage: /todo add <task> | /todo list | /todo done <id> | /todo delete <id>')
            continue
        if line.startswith('/ask'):
            query = line[len('/ask'):].strip()
            result = code_explain(query)
            if result:
                code, expl = result
                print(code)
                print(expl)
            else:
                print("I'm not sure yet, want to teach me this?")
                ans = input('[y/N]: ').strip().lower()
                if ans.startswith('y'):
                    lang = input('Language: ').strip()
                    desc = query
                    print('Enter code (end with blank line):')
                    lines = []
                    while True:
                        ln = input()
                        if not ln:
                            break
                        lines.append(ln)
                    code_text = '\n'.join(lines)
                    explanation = input('Explanation: ').strip()
                    add_example(lang, desc, code_text, explanation)
                    print('Thanks, stored!')
            continue
        if line.startswith('/code'):
            task = line[len('/code'):].strip()
            result = code_lookup(task)
            if result:
                code, expl = result
                print(code)
                print(expl)
            else:
                print("I'm not sure yet, want to teach me this?")
                ans = input('[y/N]: ').strip().lower()
                if ans.startswith('y'):
                    lang = input('Language: ').strip()
                    desc = task
                    print('Enter code (end with blank line):')
                    lines = []
                    while True:
                        ln = input()
                        if not ln:
                            break
                        lines.append(ln)
                    code_text = '\n'.join(lines)
                    explanation = input('Explanation: ').strip()
                    add_example(lang, desc, code_text, explanation)
                    print('Thanks, stored!')
            continue
        if line.startswith('/debug'):
            err = line[len('/debug'):].strip()
            fix = debug_lookup(err)
            if fix:
                print(fix)
            else:
                print("I don't know this error yet.")
            continue
        if line.startswith('/teachcode'):
            lang = input('Language: ').strip()
            desc = input('Description: ').strip()
            print('Enter code (end with blank line):')
            lines = []
            while True:
                ln = input()
                if not ln:
                    break
                lines.append(ln)
            code_text = '\n'.join(lines)
            explanation = input('Explanation: ').strip()
            add_example(lang, desc, code_text, explanation)
            print('Example saved.')
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
                found = code_explain(heard)
                if found:
                    resp = f"{found[0]}\n{found[1]}"
                else:
                    resp = get_reply(heard)
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
