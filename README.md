# emacs_pool.py
Emacs daemon pool for working with client in non-client experience

Inspired by and idea from : https://github.com/cfal/emacs-pool

See my startup configuration : https://github.com/mbaranchik/emacs.init

## Installation

* Clone repo :

    ```
    cd ~
    git clone https://github.com/mbaranchik/emacs_pool.py.git
    ```

* Link files to bin dir :

    ```
    mkdir -p ~/bin
    ln -s ~/emacs_pool.py/emacs.run ~/bin/
    ln -s ~/emacs_pool.py/emacs_pool_client.py ~/bin/
    ln -s ~/emacs_pool.py/emacs_pool_server.py ~/bin/
    ```

* Edit ~/bin/emacs.run :

    ```
    # Change EMACS_POOL_EMACS_PATH according to emacs executable location
    # Change EMACS_POOL_SIZE to desired daemon pool size
    ```
* Edit shell profile :

    * tcsh (~/.cshrc or similar):
        ```
        setenv PATH "${HOME}/bin:${PATH}"
        alias emacs_start '~/bin/emacs.run start'
        alias emacs_kill '~/bin/emacs.run kill'
        alias emacs '~/bin/emacs.run file'
        alias emacs_nw '~/bin/emacs.run nw'
        alias e 'emacs \!* &'
        alias et 'emacs_nw \!*'
        setenv ALTERNATE_EDITOR ""
        setenv EDITOR "~/bin/emacs.run nw" # $EDITOR should open in terminal
        setenv VISUAL "~/bin/emacs.run file" # $VISUAL opens in GUI with non-daemon as alternate
        ```

    * bash/zsh (~/.bashrc or ~/.zshrc):
        ```
        export PATH="${HOME}/bin:${PATH}"
        emacs_start() { # Start deamon pool (auto-run on-demand)
            emacs.run start
        }
        emacs_kill() { # Kill daemon pool
            emacs.run kill
        }
        emacs() {
            emacs.run file $*
        }
        e() {
            emacs $* &
        }
        et() { # Emacs Terminal Mode
            emacs.run nw $*
        }
        export ALTERNATE_EDITOR=""
        export EDITOR='emacs.run nw'
        export VISUAL='emacs.run file'
        ```
