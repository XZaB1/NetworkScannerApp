' —оздает €рлык в текущей папке
Set WshShell = WScript.CreateObject("WScript.Shell")
strCurrentDir = Replace(WScript.ScriptFullName, WScript.ScriptName, "")

' ѕуть к exe файлу
strExePath = strCurrentDir & "NetworkScanner v4.1\dist\NetworkScannerAI.exe"
strIconPath = strCurrentDir & "NetworkScanner v4.1\br_logo.ico"

' —оздаем €рлык
strShortcut = strCurrentDir & "NetworkScannerApp.lnk"
Set oShellLink = WshShell.CreateShortcut(strShortcut)

oShellLink.TargetPath = strExePath
oShellLink.WorkingDirectory = strCurrentDir & "NetworkScanner v4.1\dist\"
oShellLink.Description = "Network Scanner AI v4.1"
oShellLink.IconLocation = strIconPath
oShellLink.Save

MsgBox "ярлык создан: " & strShortcut, vbInformation, "√отово"