NanoBASIC’s grammar is based on the original Tiny BASIC grammar published by Dennis Allison, the creator of the first Tiny BASIC implementation, in 1976.

```
<line> ::= <number> <statement> '\n' | 'REM' .*'\n'
<statement> ::= 'PRINT' <expr-list> |
    'IF' <boolean-expr> 'THEN' <statement> |
    'GOTO' <expression> |
    'INPUT' <var> |
    'LET' <var> '=' <expression> |
    'GOSUB' <expression> |
    'RETURN'
    'CLEAR'
    'LIST'
    'RUN'
    'END'
<expr-list> ::= (<string> | <expression>) (',' (<string> | <expression>))*
<expression> ::= <term> (('+'|'-') <term>)*
<term> ::= <factor> (('*'|'/') <factor>)*
<factor> ::= ('-'|ε) <factor> | <var> | <number> | '('<expression>')'
<var> ::= ('_'|<letter>) ('_'|<letter>)*
<number> ::= <digit> <digit>*
<digit> ::= '0' | '1' | ... | '8' | '9'
<letter> ::= 'a'|'b'| ... |'y'|'z'|'A'|'B'| ... |'Y'|'Z'
<relop> ::= '<' ('>'|'='|ε) | '>' ('<'|'='|ε) | '='
<boolean-expr> ::= <expression> <relop> <expression>
<string> ::= '"' .* '"'
```

Where epsilon (`ε`) indicates that the corresponding *or* component could be empty.
