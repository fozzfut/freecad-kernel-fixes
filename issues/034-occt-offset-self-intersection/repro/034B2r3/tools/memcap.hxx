// memcap.hxx - puts the harness process into a Job Object with a 1 GB committed-memory cap (AGENT-RULES: every test
// process <= 1 GB). Beyond the cap allocations fail (Standard_OutOfMemory / bad_alloc) -> the run is recorded as
// "not measured: RAM budget", never raised.
#pragma once
#include <windows.h>
struct MemCap034b
{
  MemCap034b()
  {
    HANDLE j = CreateJobObjectW(nullptr, nullptr);
    if (!j) return;
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION li = {};
    li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY;
    li.ProcessMemoryLimit = (SIZE_T)1024 * 1024 * 1024;
    SetInformationJobObject(j, JobObjectExtendedLimitInformation, &li, sizeof(li));
    AssignProcessToJobObject(j, GetCurrentProcess());
  }
};
static MemCap034b g_memcap034b;
// Lane B2: in-process wall-clock watchdog (Git Bash 'timeout' does not reliably kill native processes):
// after B2_TMO seconds (default 60) the process prints "R HANG" and terminates itself with code 124.
#include <cstdio>
#include <cstdlib>
static DWORD WINAPI watchdog034b2(LPVOID p)
{
  Sleep((DWORD)(size_t)p);
  printf("R HANG watchdog\n");
  fflush(stdout);
  TerminateProcess(GetCurrentProcess(), 124);
  return 0;
}
struct Watchdog034b2
{
  Watchdog034b2()
  {
    const char* e = getenv("B2_TMO");
    int s = e ? atoi(e) : 60;
    if (s > 0) CreateThread(nullptr, 0, watchdog034b2, (LPVOID)(size_t)(s * 1000), 0, nullptr);
  }
};
static Watchdog034b2 g_watchdog034b2;
