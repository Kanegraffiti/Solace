from .modes.diary_mode import add_entry
from .modes.teaching_mode import add_fact, add_snippet
from .modes.chat_mode import chat, ChatLockedError
from .logic.coder import generate_code
from .logic.importer import process_file
from .logic.asker import get_answer
from .logic.converse import get_reply
from .utils.voice import speak, recognize_speech

HELP_TEXT = """Commands:
/mode diary   - enter diary mode
/mode teach   - enter teaching mode
/mode chat    - chat with Solace (requires 10 diary entries)
/ask <q>      - ask a coding question
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
        if line.startswith('/ask'):
            question = line[len('/ask'):].strip()
            response = get_answer(question)
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
            mood = add_entry(line)
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
