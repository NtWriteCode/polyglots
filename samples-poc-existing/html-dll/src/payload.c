/* Stands in for the StrelaStealer DLL. Run() only prints a message.
 * Entry point for `rundll32 polyglot.html,Run`, so it has rundll32's signature. */
#include <windows.h>
#include <stdio.h>

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID reserved)
{
    return TRUE;
}

__declspec(dllexport) void CALLBACK Run(HWND hwnd, HINSTANCE hinst, LPSTR cmdline, int show)
{
    puts("This came from the DLL side of the polyglot");
    fflush(stdout);
    MessageBoxA(NULL, "This came from the DLL side of the polyglot", "Polyglot POC", MB_OK);
}
