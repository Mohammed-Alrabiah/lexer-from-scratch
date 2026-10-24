# Lexical Analyzer from Scratch — Regex → NFA → DFA → Tokens

A table-driven lexical analyzer written in pure Python with **no regex library**. Token rules are given as regular expressions; the program parses them, builds NFAs with Thompson's construction, merges them into a single DFA with subset construction, and tokenizes source text with maximal munch and priority-based tie-breaking.

Group term project for **CSC 339 — Theory of Computation**, King Saud University (Spring 2026).
Team: Mohammed Alrabiah · Feras Alnasser · Faisal Alzamil

```
regex strings ──► implicit-concat insertion ──► shunting-yard (infix → postfix)
      ──► Thompson's construction (one NFA per token) ──► ε-linked "super NFA"
      ──► subset construction ──► DFA ──► maximal-munch scanner ──► token stream
```

## Example

Token specification (keywords listed before `ID` so they win ties):

```
("KW_IF", "if"),
("KW_THEN", "then"),
("KW_ELSE", "else"),
("ID", "[A-Za-z][A-Za-z0-9_]*"),
("NUM", "[0-9]+(\.[0-9]+)?"),
("ASSIGN", "="),
("OP_GT", ">"),
...
```

Input: `if x > y then {x=y; z=x-1} else x=y+5`

```
Lexeme          | Token           | Position
--------------------------------------------------
'if'            | KW_IF           | Line 1, col 1
'x'             | ID              | Line 1, col 4
'>'             | OP_GT           | Line 1, col 6
'y'             | ID              | Line 1, col 8
'then'          | KW_THEN         | Line 1, col 10
'{'             | LBRACE          | Line 1, col 15
'x'             | ID              | Line 1, col 16
'='             | ASSIGN          | Line 1, col 17
...
'5'             | NUM             | Line 1, col 37
```

An unrecognised character is reported with its exact position:

```
[!] Lexing Error: Unrecognized char '.' at Line 1, Col 20
```

## How it works

**1. Regex parsing.** The rule's regex is tokenised (character classes and `\`-escapes are kept as single units), an explicit concatenation operator is inserted between adjacent atoms, and the shunting-yard algorithm converts the result to postfix with precedence `* + ?` > concat > `|`.

**2. Thompson's construction.** The postfix expression is evaluated on a stack of NFA fragments. Each operator (`·`, `|`, `*`, `+`, `?`) combines fragments by adding a constant number of states and ε-transitions, so the NFA is linear in the length of the regex.

**3. Super NFA.** Each token's NFA gets an accepting state tagged with the token name and a *priority* equal to its position in the spec list; all NFAs are joined under one start state via ε-transitions.

**4. Subset construction.** ε-closure and `move` convert the super NFA into a DFA whose states are frozensets of NFA states. When a DFA state contains several accepting NFA states, the one with the lowest priority number wins — this is how `if` is lexed as `KW_IF` rather than `ID`.

**5. Maximal munch.** The scanner walks the DFA from the current position as far as it can, remembering the last accepting state it passed, then emits that longest match and resumes after it. Whitespace is skipped while line/column counters are maintained.

Supported regex syntax: literals, `\`-escapes, grouping `( )`, union `|`, `*`, `+`, `?`, and the character classes `[A-Za-z]`, `[0-9]`, `[A-Za-z0-9_]` (other bracket expressions are treated as literal sets).

## Complexity

| Stage | Time | Space |
|---|---|---|
| NFA construction | O(\|R\|) | O(\|R\|) |
| Subset construction | O(2^\|Q\|) worst case | O(2^\|Q\| · \|Σ\|) worst case |
| Scanning | O(N) | O(1) auxiliary |

where \|R\| is the combined regex length, \|Q\| the number of NFA states and N the input length. In practice the DFA for a typical language spec is small; the exponential bound is the usual subset-construction worst case.

## Running it

Python 3 only, no dependencies.

```bash
python lexer.py
```

The interactive menu lets you add rules one at a time (option 1) or paste a whole list in the `("NAME", "regex"),` format and end with `DONE` (option 2), compile the DFA (option 3), then enter source text to tokenise (option 4). A ready-made spec is in [`examples/toy_language.txt`](examples/toy_language.txt).

## Limitations and future work

- Subset construction can blow up on highly ambiguous rule sets; DFA minimisation (Hopcroft's algorithm) would reduce the table size.
- Scanning halts at the first lexical error; panic-mode recovery (skip to the next delimiter) would allow reporting all errors in one pass.
- Character classes are limited to the three predefined ranges plus literal sets; general `[a-f]`-style ranges are not parsed.

## Report

The full write-up — data structures, pseudocode, cost analysis, sample runs and user manual — is in [`docs/report.pdf`](docs/report.pdf).
