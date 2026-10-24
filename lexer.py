import sys


# ==========================================
# 1. DATA STRUCTURES (STATE & NFA)
# ==========================================

class State:
    _id_counter = 0

    def __init__(self):
        self.id = State._id_counter
        State._id_counter += 1
        self.transitions = {}
        self.e_transitions = set()
        self.is_accepting = False
        self.token_type = None
        self.priority = float('inf')

    def add_transition(self, char, state):
        if char not in self.transitions:
            self.transitions[char] = set()
        self.transitions[char].add(state)


class NFA:
    def __init__(self, start_state, accept_state):
        self.start = start_state
        self.accept = accept_state


# ==========================================
# 2. THOMPSON'S CONSTRUCTION PRIMITIVES
# ==========================================

def build_char_nfa(char):
    start, accept = State(), State()
    start.add_transition(char, accept)
    return NFA(start, accept)


def build_range_nfa(chars):
    start, accept = State(), State()
    for c in chars:
        start.add_transition(c, accept)
    return NFA(start, accept)


def build_concat_nfa(nfa1, nfa2):
    nfa1.accept.e_transitions.add(nfa2.start)
    nfa1.accept.is_accepting = False
    return NFA(nfa1.start, nfa2.accept)


def build_union_nfa(nfa1, nfa2):
    start, accept = State(), State()
    start.e_transitions.update([nfa1.start, nfa2.start])
    nfa1.accept.e_transitions.add(accept)
    nfa2.accept.e_transitions.add(accept)
    nfa1.accept.is_accepting = False
    nfa2.accept.is_accepting = False
    return NFA(start, accept)


def build_star_nfa(nfa):
    start, accept = State(), State()
    start.e_transitions.update([nfa.start, accept])
    nfa.accept.e_transitions.add(accept)
    accept.e_transitions.add(start)
    nfa.accept.is_accepting = False
    return NFA(start, accept)


def build_plus_nfa(nfa):
    start, accept = State(), State()
    start.e_transitions.add(nfa.start)
    nfa.accept.e_transitions.add(accept)
    accept.e_transitions.add(start)
    nfa.accept.is_accepting = False
    return NFA(start, accept)


def build_optional_nfa(nfa):
    start, accept = State(), State()
    start.e_transitions.update([nfa.start, accept])
    nfa.accept.e_transitions.add(accept)
    nfa.accept.is_accepting = False
    return NFA(start, accept)


# ==========================================
# 3. REGEX PARSER (Infix -> Postfix -> NFA)
# ==========================================

def expand_range(range_str):
    chars = set()
    if range_str == "[A-Za-z]":
        chars.update(chr(i) for i in range(65, 91))
        chars.update(chr(i) for i in range(97, 123))
    elif range_str == "[0-9]":
        chars.update(str(i) for i in range(10))
    elif range_str == "[A-Za-z0-9_]":
        chars.update(chr(i) for i in range(65, 91))
        chars.update(chr(i) for i in range(97, 123))
        chars.update(str(i) for i in range(10))
        chars.add('_')
    else:
        chars.update(list(range_str.strip('[]')))
    return list(chars)


def insert_implicit_concat(regex):
    result = []
    i = 0
    while i < len(regex):
        char = regex[i]
        if char == '[':
            end = regex.find(']', i)
            result.append(regex[i:end + 1])
            i = end + 1
        elif char == '\\':
            result.append(regex[i:i + 2])
            i += 2
        else:
            result.append(char)
            i += 1

    final_res = []
    for i in range(len(result)):
        final_res.append(result[i])
        if i + 1 < len(result):
            c1, c2 = result[i], result[i + 1]
            if c1 not in ['(', '|'] and c2 not in [')', '|', '*', '+', '?']:
                final_res.append('·')
    return final_res


def to_postfix(tokens):
    precedence = {'*': 3, '+': 3, '?': 3, '·': 2, '|': 1}
    output, stack = [], []
    for token in tokens:
        if token in ['*', '+', '?', '·', '|']:
            while (stack and stack[-1] != '(' and
                   precedence.get(stack[-1], 0) >= precedence.get(token, 0)):
                output.append(stack.pop())
            stack.append(token)
        elif token == '(':
            stack.append(token)
        elif token == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            stack.pop()
        else:
            output.append(token)
    while stack:
        output.append(stack.pop())
    return output


def regex_to_nfa(regex_str):
    tokens = insert_implicit_concat(regex_str)
    postfix = to_postfix(tokens)
    stack = []

    for token in postfix:
        if token == '*':
            stack.append(build_star_nfa(stack.pop()))
        elif token == '+':
            stack.append(build_plus_nfa(stack.pop()))
        elif token == '?':
            stack.append(build_optional_nfa(stack.pop()))
        elif token == '·':
            n2, n1 = stack.pop(), stack.pop()
            stack.append(build_concat_nfa(n1, n2))
        elif token == '|':
            n2, n1 = stack.pop(), stack.pop()
            stack.append(build_union_nfa(n1, n2))
        elif token.startswith('['):
            stack.append(build_range_nfa(expand_range(token)))
        elif token.startswith('\\'):
            stack.append(build_char_nfa(token[1]))
        else:
            stack.append(build_char_nfa(token))

    return stack.pop()


# ==========================================
# 4. SUBSET CONSTRUCTION (NFA -> DFA)
# ==========================================

def e_closure(states):
    stack, closure = list(states), set(states)
    while stack:
        curr = stack.pop()
        for nxt in curr.e_transitions:
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure


def move(states, symbol):
    reachable = set()
    for s in states:
        if symbol in s.transitions:
            reachable.update(s.transitions[symbol])
    return reachable


def build_dfa(super_start):
    init_closure = e_closure({super_start})
    dfa_start_id = frozenset(init_closure)

    unmarked = [init_closure]
    dfa_map = {dfa_start_id: init_closure}
    dfa_trans, dfa_accept = {}, {}

    while unmarked:
        curr_nfa_states = unmarked.pop(0)
        curr_dfa_id = frozenset(curr_nfa_states)
        dfa_trans[curr_dfa_id] = {}

        best_pri, winning_tok = float('inf'), None
        for s in curr_nfa_states:
            if s.is_accepting and s.priority < best_pri:
                best_pri = s.priority
                winning_tok = s.token_type
        if winning_tok:
            dfa_accept[curr_dfa_id] = winning_tok

        symbols = set()
        for s in curr_nfa_states:
            symbols.update(s.transitions.keys())

        for sym in symbols:
            nxt_nfa_states = e_closure(move(curr_nfa_states, sym))
            if not nxt_nfa_states: continue

            nxt_dfa_id = frozenset(nxt_nfa_states)
            if nxt_dfa_id not in dfa_map:
                dfa_map[nxt_dfa_id] = nxt_nfa_states
                unmarked.append(nxt_nfa_states)
            dfa_trans[curr_dfa_id][sym] = nxt_dfa_id

    return dfa_start_id, dfa_trans, dfa_accept


# ==========================================
# 5. SIMULATION (MAXIMAL MUNCH)
# ==========================================

def simulate(source, dfa_start, dfa_trans, dfa_accept):
    pos, line, col = 0, 1, 1
    print(f"\n{'-' * 50}\n{'Lexeme':<15} | {'Token':<15} | Position\n{'-' * 50}")

    while pos < len(source):
        char = source[pos]
        if char in ' \t\n\r':
            if char == '\n':
                line += 1
                col = 1
            else:
                col += 1
            pos += 1
            continue

        curr_dfa = dfa_start
        last_acc_state, last_acc_pos = None, -1
        lookahead = pos

        while lookahead < len(source):
            l_char = source[lookahead]
            if curr_dfa in dfa_trans and l_char in dfa_trans[curr_dfa]:
                curr_dfa = dfa_trans[curr_dfa][l_char]
                if curr_dfa in dfa_accept:
                    last_acc_state = curr_dfa
                    last_acc_pos = lookahead
                lookahead += 1
            else:
                break

        if last_acc_state:
            lexeme = source[pos:last_acc_pos + 1]
            tok = dfa_accept[last_acc_state]
            print(f"'{lexeme}'{'' :<{13 - len(lexeme)}} | {tok:<15} | Line {line}, col {col}")
            col += len(lexeme)
            pos = last_acc_pos + 1
        else:
            print(f"[!] Lexing Error: Unrecognized char '{source[pos]}' at Line {line}, Col {col}")
            return
    print("-" * 50)


# ==========================================
# 6. CLI AND BULK PARSING LOGIC
# ==========================================

def parse_bulk_input(bulk_text):
    """Safely extracts Token and Regex from raw text without the re module."""
    # Normalize smart quotes that often occur from copy-pasting
    normalized = bulk_text.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")

    extracted_specs = []
    lines = normalized.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split by quotes. A correctly formatted line like ("NAME", "REGEX")
        # will yield at least 5 segments when split by '"'
        parts = line.split('"')
        if len(parts) >= 5:
            name = parts[1]
            regex = parts[3]
            extracted_specs.append((name, regex))
        else:
            print(f"[!] Ignored malformed line: {line}")

    return extracted_specs


def main():
    specs = []
    dfa_ready = False
    dfa_s, dfa_t, dfa_a = None, None, None

    while True:
        print("\n=== Lexical Analyzer CLI ===")
        print("1. Add Single Token Specification")
        print("2. Add Bulk Token Specifications (Paste a list)")
        print("3. Compile Lexer (Build DFA)")
        print("4. Input Source Code & Run Lexer")
        print("5. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            name = input("Enter Token Name (e.g., ID): ")
            regex = input("Enter Regex (e.g., [A-Za-z][A-Za-z0-9_]*): ")
            specs.append((name, regex))
            dfa_ready = False
            print(f"Added {name} -> {regex}")

        elif choice == '2':
            print("Paste your bulk specifications below.")
            print("Format must be: (\"TOKEN_NAME\", \"regex\"),")
            print("Type 'DONE' on a new line and press Enter when finished:")

            bulk_lines = []
            while True:
                try:
                    line = input()
                    if line.strip().upper() == 'DONE':
                        break
                    bulk_lines.append(line)
                except EOFError:
                    break

            new_specs = parse_bulk_input('\n'.join(bulk_lines))
            for name, regex in new_specs:
                specs.append((name, regex))
                print(f"Added {name} -> {regex}")
            if new_specs:
                dfa_ready = False

        elif choice == '3':
            if not specs:
                print("No specifications loaded!")
                continue
            super_start = State()
            for priority, (name, regex) in enumerate(specs, 1):
                try:
                    nfa = regex_to_nfa(regex)
                    nfa.accept.is_accepting = True
                    nfa.accept.token_type = name
                    nfa.accept.priority = priority
                    super_start.e_transitions.add(nfa.start)
                except Exception as e:
                    print(f"Error compiling {name} (Check regex syntax): {e}")
            dfa_s, dfa_t, dfa_a = build_dfa(super_start)
            dfa_ready = True
            print("DFA Compilation Successful.")

        elif choice == '4':
            if not dfa_ready:
                print("Please compile the Lexer (Option 3) first.")
                continue
            source = input("Enter source code string: ")
            simulate(source, dfa_s, dfa_t, dfa_a)

        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()