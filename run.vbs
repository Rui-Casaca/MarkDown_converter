Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batchFile = scriptDir & "\scripts\run_aux.bat"

shell.CurrentDirectory = scriptDir
shell.Run Chr(34) & batchFile & Chr(34), 0, False
