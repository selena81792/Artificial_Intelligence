# Server for the Intro to AI module

## Description of the game

You can find the rules of the game [Here](https://github.com/nlehir/phantom_opera/blob/master/le-fantome-de-l-opera_rules_fr.pdf)

## 🚀 Structure of the projet

In the project you'll find the following structure:

```
/
├── .gitignore
├── README.md 
└── The phantom of the Opera.pdf
└── happy_fantom.py
└── happy_inspector.py
```

## To launch a game

| Command         | Action                                              |
|:----------------|:--------------------------------------------        |
| `python3.6 server.py`   | Runs the Server                             |
| `python3.6 happy_inspector.py` | Runs the inspector                   |
| `python3.6 happy_fantom.py` | Runs the fantom                         |

You need to follow this order. 
You can us three tabs of your favorite terminal.
You can also use a more recent version of python.

## Additional information 

You can set the level of importance of the logging messages : 
- sent to text files
- sent to the console

## Difference between game and server
Brown character : takes the moved character to his final position, instead of
any position on the path taken by the brown character.