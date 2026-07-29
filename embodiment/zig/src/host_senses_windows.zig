//! Windows host capture — live desktop framebuffer + mic (Zig → Win32).
//! Display: GDI BitBlt of desktop DC (compositor output sample, not a PNG file).
//! Mic: winmm waveIn short buffer.
//! Link: -lgdi32 -luser32 -lwinmm

const std = @import("std");

const WINAPI: std.builtin.CallingConvention = .winapi;
const BOOL = i32;
const DWORD = u32;
const UINT = u32;
const HWND = ?*anyopaque;
const HDC = ?*anyopaque;
const HBITMAP = ?*anyopaque;
const HGDIOBJ = ?*anyopaque;

const SRCCOPY: DWORD = 0x00CC0020;
const DIB_RGB_COLORS: UINT = 0;
const BI_RGB: DWORD = 0;
const SM_CXSCREEN: i32 = 0;
const SM_CYSCREEN: i32 = 1;

const BITMAPINFOHEADER = extern struct {
    biSize: DWORD,
    biWidth: i32,
    biHeight: i32,
    biPlanes: u16,
    biBitCount: u16,
    biCompression: DWORD,
    biSizeImage: DWORD,
    biXPelsPerMeter: i32,
    biYPelsPerMeter: i32,
    biClrUsed: DWORD,
    biClrImportant: DWORD,
};

const BITMAPINFO = extern struct {
    bmiHeader: BITMAPINFOHEADER,
    bmiColors: [1]DWORD,
};

extern "user32" fn GetDesktopWindow() callconv(WINAPI) *anyopaque;
extern "user32" fn GetDC(hWnd: HWND) callconv(WINAPI) HDC;
extern "user32" fn ReleaseDC(hWnd: HWND, hDC: HDC) callconv(WINAPI) i32;
extern "user32" fn GetSystemMetrics(nIndex: i32) callconv(WINAPI) i32;

extern "gdi32" fn CreateCompatibleDC(hdc: HDC) callconv(WINAPI) HDC;
extern "gdi32" fn CreateCompatibleBitmap(hdc: HDC, cx: i32, cy: i32) callconv(WINAPI) HBITMAP;
extern "gdi32" fn SelectObject(hdc: HDC, h: HGDIOBJ) callconv(WINAPI) HGDIOBJ;
extern "gdi32" fn BitBlt(hdc: HDC, x: i32, y: i32, cx: i32, cy: i32, hdcSrc: HDC, x1: i32, y1: i32, rop: DWORD) callconv(WINAPI) BOOL;
extern "gdi32" fn GetDIBits(hdc: HDC, hbm: HBITMAP, start: UINT, cLines: UINT, lpvBits: ?*anyopaque, lpbmi: *BITMAPINFO, usage: UINT) callconv(WINAPI) i32;
extern "gdi32" fn DeleteObject(ho: HGDIOBJ) callconv(WINAPI) BOOL;
extern "gdi32" fn DeleteDC(hdc: HDC) callconv(WINAPI) BOOL;

/// Capture a downscaled live desktop region into grayscale out_gray; sets w,h.
pub fn captureDisplay(out_gray: []u8, out_w: *usize, out_h: *usize) bool {
    out_w.* = 0;
    out_h.* = 0;
    const desk = GetDesktopWindow();
    const hdc_screen = GetDC(desk);
    if (hdc_screen == null) return false;
    defer _ = ReleaseDC(desk, hdc_screen);

    const sw = GetSystemMetrics(SM_CXSCREEN);
    const sh = GetSystemMetrics(SM_CYSCREEN);
    if (sw <= 0 or sh <= 0) return false;

    // Use top-left of desktop at fixed tile size (live compositor pixels).
    // Capture a fixed tile from desktop origin (live compositor pixels).
    // Full multi-monitor / DXGI path later; GDI is enough to wire the afferent.
    const tw: i32 = @min(64, sw);
    const th: i32 = @min(36, sh);

    const hdc_mem = CreateCompatibleDC(hdc_screen);
    if (hdc_mem == null) return false;
    defer _ = DeleteDC(hdc_mem);

    const hbmp = CreateCompatibleBitmap(hdc_screen, tw, th);
    if (hbmp == null) return false;
    defer _ = DeleteObject(hbmp);

    const old = SelectObject(hdc_mem, hbmp);
    defer _ = SelectObject(hdc_mem, old);

    if (BitBlt(hdc_mem, 0, 0, tw, th, hdc_screen, 0, 0, SRCCOPY) == 0) return false;

    var bmi: BITMAPINFO = std.mem.zeroes(BITMAPINFO);
    bmi.bmiHeader.biSize = @sizeOf(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = tw;
    bmi.bmiHeader.biHeight = -th; // top-down
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    var bgra: [64 * 36 * 4]u8 = undefined;
    const got = GetDIBits(hdc_mem, hbmp, 0, @intCast(th), &bgra, &bmi, DIB_RGB_COLORS);
    if (got == 0) return false;

    const npix: usize = @intCast(tw * th);
    if (out_gray.len < npix) return false;
    var i: usize = 0;
    while (i < npix) : (i += 1) {
        const o = i * 4;
        const b = bgra[o];
        const g = bgra[o + 1];
        const r = bgra[o + 2];
        out_gray[i] = @intCast((@as(u32, r) * 30 + @as(u32, g) * 59 + @as(u32, b) * 11) / 100);
    }
    out_w.* = @intCast(tw);
    out_h.* = @intCast(th);
    return true;
}

const WAVEFORMATEX = extern struct {
    wFormatTag: u16,
    nChannels: u16,
    nSamplesPerSec: DWORD,
    nAvgBytesPerSec: DWORD,
    nBlockAlign: u16,
    wBitsPerSample: u16,
    cbSize: u16,
};

const WAVEHDR = extern struct {
    lpData: ?[*]u8,
    dwBufferLength: DWORD,
    dwBytesRecorded: DWORD,
    dwUser: usize,
    dwFlags: DWORD,
    dwLoops: DWORD,
    lpNext: ?*WAVEHDR,
    reserved: usize,
};

const HWAVEIN = ?*anyopaque;
const MMSYSERR_NOERROR: u32 = 0;
const WAVE_FORMAT_PCM: u16 = 1;
const WAVE_MAPPER: u32 = 0xFFFFFFFF;
const CALLBACK_NULL: DWORD = 0;

extern "winmm" fn waveInOpen(
    phwi: *HWAVEIN,
    uDeviceID: u32,
    pwfx: *const WAVEFORMATEX,
    dwCallback: usize,
    dwInstance: usize,
    fdwOpen: DWORD,
) callconv(WINAPI) u32;
extern "winmm" fn waveInPrepareHeader(hwi: HWAVEIN, pwh: *WAVEHDR, cbwh: UINT) callconv(WINAPI) u32;
extern "winmm" fn waveInAddBuffer(hwi: HWAVEIN, pwh: *WAVEHDR, cbwh: UINT) callconv(WINAPI) u32;
extern "winmm" fn waveInStart(hwi: HWAVEIN) callconv(WINAPI) u32;
extern "winmm" fn waveInStop(hwi: HWAVEIN) callconv(WINAPI) u32;
extern "winmm" fn waveInReset(hwi: HWAVEIN) callconv(WINAPI) u32;
extern "winmm" fn waveInUnprepareHeader(hwi: HWAVEIN, pwh: *WAVEHDR, cbwh: UINT) callconv(WINAPI) u32;
extern "winmm" fn waveInClose(hwi: HWAVEIN) callconv(WINAPI) u32;

/// Capture up to out_pcm.len mono i16 samples at 16 kHz; returns count.
pub fn captureMic(out_pcm: []i16) usize {
    if (out_pcm.len == 0) return 0;
    var fmt: WAVEFORMATEX = .{
        .wFormatTag = WAVE_FORMAT_PCM,
        .nChannels = 1,
        .nSamplesPerSec = 16000,
        .nAvgBytesPerSec = 16000 * 2,
        .nBlockAlign = 2,
        .wBitsPerSample = 16,
        .cbSize = 0,
    };
    var hwi: HWAVEIN = null;
    if (waveInOpen(&hwi, WAVE_MAPPER, &fmt, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) return 0;
    defer _ = waveInClose(hwi);

    const nbytes: DWORD = @intCast(out_pcm.len * 2);
    var hdr: WAVEHDR = std.mem.zeroes(WAVEHDR);
    hdr.lpData = @ptrCast(out_pcm.ptr);
    hdr.dwBufferLength = nbytes;

    if (waveInPrepareHeader(hwi, &hdr, @sizeOf(WAVEHDR)) != MMSYSERR_NOERROR) return 0;
    defer _ = waveInUnprepareHeader(hwi, &hdr, @sizeOf(WAVEHDR));

    if (waveInAddBuffer(hwi, &hdr, @sizeOf(WAVEHDR)) != MMSYSERR_NOERROR) return 0;
    if (waveInStart(hwi) != MMSYSERR_NOERROR) return 0;

    const wait_ms: u64 = @min(250, 50 + (out_pcm.len * 1000) / 16000);
    std.Thread.sleep(wait_ms * std.time.ns_per_ms);

    _ = waveInStop(hwi);
    _ = waveInReset(hwi);

    const rec = hdr.dwBytesRecorded / 2;
    return @min(out_pcm.len, rec);
}
