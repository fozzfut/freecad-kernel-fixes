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
