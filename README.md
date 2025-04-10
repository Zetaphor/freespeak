# FreeSpeak

A simple voice dictation application for Linux that captures audio, transcribes it, corrects grammar, and types the result into the currently active window.

I built this as an simple alternative to [Talon](https://talonvoice.com) since that does not support Wayland.

## Features

*   **DBus Control:** Exposes a DBus interface (`org.voice.Dictation`) for potential external control (e.g., toggling recording). Includes a shell script to toggle recording that can be bound to a hotkey.
*   **Voice Activity Detection (VAD):** Only processes audio when speech is detected.
*   **Grammar Correction:** Leverages LanguageTool (`src/langtool.py`) to improve punctuation and grammar of the transcribed text.
*   **System-Wide Typing:** Uses `ydotool` to simulate keyboard input, allowing dictation into any application.

## Installation

1.  **Install Python dependencies:**

    ```bash
    uv sync
    uv run src/main.py
    ```

2.  **Install System Dependencies:**

    ```bash
    # Fedora
    sudo dnf install ydotool
    ```

3.  **Configure ydotool:**

    To simulate typing, the program needs access to your /dev/uinput device. By default, this requires root privileges every time you run ydotool, so you'd have to enter your password every time you run this application.

    To avoid that, you can give the program permanent access to the input device by adding your username to the input user group on your system and giving the group write access to the uinput device.

    To do that, we use a udev rule. Udev is the Linux system that detects and reacts to devices getting plugged or unplugged on your computer. It also works with virtual devices like ydotool.

    To add the current `$USER` to a group, you can use the usermod command:

    ```bash
    # Set permissions (might be needed depending on your setup)
    # sudo gpasswd -a $USER input # Add user to 'input' group, then log out/in

    # Start and enable the user service
    systemctl --user enable ydotoold.service
    systemctl --user start ydotoold.service

    # Verify it's running
    systemctl --user status ydotoold.service
    ```

    You then need to define a new udev rule that will give the input group permanent write access to the uinput device (this will give ydotool write access too).

    #### Solution by https://github.com/ReimuNotMoe/ydotool/issues/25#issuecomment-535842993

    ```bash
    echo '## Give ydotoold access to the uinput device
    KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
    ' | sudo tee /etc/udev/rules.d/80-uinput.rules > /dev/null
    ```

    You will need to restart your computer for the change to take effect.

    Finally, ydotool works with a daemon that you leave running in the background, ydotoold, for performance reasons. You needs to run ydotoold before you start using ydotool.

    ```bash
    systemctl --user enable ydotoold.service
    systemctl --user start ydotoold.service
    ```

4.  **Set up LanguageTool:**
    A docker-compose.yml file is provided to start a LanguageTool server.

    ```bash
    docker-compose up -d
    ```

    ### N-gram datasets

    You will want to add the ngram dataset for your language to improve the grammar correction.

    > LanguageTool can make use of large n-gram data sets to detect errors with words that are often confused, like their and there.

    Source: https://dev.languagetool.org/finding-errors-using-n-gram-data

    [Download](http://languagetool.org/download/ngram-data/) the ngram dataset for your language and put it in the `languagetool/ngrams` directory.

    ```
    languagetool/
    ├─ ngrams/
    │  ├─ en/
    │  │  ├─ 1grams/
    │  │  ├─ 2grams/
    │  │  ├─ 3grams/
    │  ├─ es/
    │  │  ├─ 1grams/
    │  │  ├─ 2grams/
    │  │  ├─ 3grams/
    ```

    ### Improving the spell checker

    > You can improve the spell checker without touching the dictionary. For single words (no spaces), you can add your words to one of these files:
    > -   `spelling.txt`: words that the spell checker will ignore and use to generate corrections if someone types a similar word
    > -   `ignore.txt`: words that the spell checker will ignore but not use to generate corrections
    > -   `prohibited.txt`: words that should be considered incorrect even though the spell checker would accept them

    Source: https://dev.languagetool.org/hunspell-support

    These files are in the `languagetool/` directory.