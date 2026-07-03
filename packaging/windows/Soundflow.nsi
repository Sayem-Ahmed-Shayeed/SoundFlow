!include "MUI2.nsh"

Name "Soundflow"
OutFile "Soundflow-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\Soundflow"
RequestExecutionLevel user
Unicode True

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Soundflow" SEC_APP
  SetOutPath "$INSTDIR"
  File /r "..\..\dist\Soundflow\*"
  CreateDirectory "$SMPROGRAMS\Soundflow"
  CreateShortcut "$SMPROGRAMS\Soundflow\Soundflow.lnk" "$INSTDIR\Soundflow.exe"
  CreateShortcut "$DESKTOP\Soundflow.lnk" "$INSTDIR\Soundflow.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Soundflow" \
    "DisplayName" "Soundflow"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Soundflow" \
    "UninstallString" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\Soundflow.lnk"
  RMDir /r "$SMPROGRAMS\Soundflow"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Soundflow"
SectionEnd

