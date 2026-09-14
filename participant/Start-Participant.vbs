On Error Resume Next
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
powerShell = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"
command = """" & powerShell & """" & " -NoProfile -STA -ExecutionPolicy Bypass -File " & """" & root & "\ParticipantLauncher.ps1" & """"
shell.Run command, 0, False
If Err.Number <> 0 Then
  MsgBox "Could not start the Zotero bridge: " & Err.Description, 16, "Zotero Read-only Bridge"
End If
