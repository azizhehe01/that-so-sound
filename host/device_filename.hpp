#pragma once
#include <cwchar>
inline bool valid_device_filename(const wchar_t* name) {
    return name && (std::wcscmp(name, L"1462134C_InternalSpeakers.nsx") == 0 ||
                    std::wcscmp(name, L"1D05E022_Speakers.nsx") == 0);
}
