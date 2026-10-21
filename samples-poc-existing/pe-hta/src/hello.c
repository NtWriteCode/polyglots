/* The PE side: prints its message and (where a desktop exists) pops it up too. */
#include <stdio.h>
#include <windows.h>

int main(void) {
    const char *msg = "This came from the PE side of the polyglot";
    puts(msg);
    fflush(stdout);
    MessageBoxA(NULL, msg, "Polyglot POC", MB_OK);
    return 0;
}
