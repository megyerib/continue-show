$vlcIni  = $env:APPDATA + "\vlc\vlc-qt-interface.ini"
$vidDir  = $args[0]
$vlcPath = "C:\Program Files\VideoLAN\VLC\vlc.exe"
$hstFile = "history.txt"
$validFileTypes = @('*.mp4', '*.mkv', '*.avi')

function getFileToPlay_vlc
{
	$return = @{}
	$return.success = $false
	
	# Get history & times
	gc $vlcIni | foreach {
		if ($_ -match "^list=(.+)$")
		{
			$history = $matches[1] -split ", "
		}
		
		if ($_ -match "^times=(.+)$")
		{
			$times = $matches[1] -split ", "
		}
	}

	# Get movie files
	$movies = gci -Path $vidDir -Include $validFileTypes -Recurse | where {! $_.PSIsContainer}

	$files = @()

	$fileNum = 0

	foreach ($movie in $movies)
	{
		$files += $movie.Name
		$fileNum++
	}

	# Get recently played movie
	$last = ""
	$hstIndex = 0
	$time = 0

	foreach ($entry in $history)
	{
		$path = $entry
		$path = $path.replace("file:///", "")
		$path = $path.replace("/", "\")
		$path = [uri]::UnescapeDataString($path)
		
		if ($path -match "^" + $vidDir.replace("\", "\\")) # Backslashes need to be escaped bc regex
		{
			$last = $path
			$time = $times[$hstIndex] / 1000
			$return.success = $true
			break
		}
		
		$hstIndex++
	}

	#Get file index to play
	$fileIndex = 0

	if ($last -ne "")
	{
		foreach ($file in $files)
		{
			if ($last -eq "$vidDir\$file" )
			{
				break
			}
			
			$fileIndex++
		}

		if ($time -eq 0) # File fully played. skip to next
		{
			$fileIndex++
		}

		if ($fileIndex -ge $fileNum)
		{
			$fileIndex = 0
			$time = 0
		}
	}
	
	$return.name = $files[$fileIndex]
	$return.time = $time
	
	return $return
}

function getFileToPlay_txt
{
	$return = @{}
	$return.success = $false
	
	gc $hstFile | foreach {
		if ($_ -match "^.+\t(.+)\t(.+)(\.\d+)?$")
		{
			$return.name    = $matches[1]
			$return.time    = $matches[2]
			$return.success = $true
		}
	}
	
	return $return
}

function getFirstFile
{
	$return = @{}
	$return.success = $true

	$movies = gci -Path $vidDir -Include $validFileTypes -Recurse | where {! $_.PSIsContainer}

	$return.name = $movies[0].Name
	$return.time = 0
	
	return $return
}

function writeHistoryTxt
{
	$res = getFileToPlay_vlc

	$historyList = gc $hstFile

	Clear-Content $hstFile

	foreach ($line in $historyList)
	{
		if ($line -notmatch "^" + $vidDir.replace("\", "\\")) # Backslashes need to be escaped bc regex
		{
			echo $line >> $hstFile
		}
	}

	$fileName = $res.name
	$time     = $res.time
	echo "$vidDir`t$fileName`t$time" >> $hstFile
}

$res = getFileToPlay_vlc

if (!$res.success)
{
	$res = getFileToPlay_txt
}
if (!$res.success)
{
	$res = getFirstFile
}

$filePath = $vidDir + "\" + $res.name
$time     = $res.time + ".0"

$params = "--start-time=$time", "`"$filePath`"", "--fullscreen"

& $vlcPath $params

Wait-Process vlc

writeHistoryTxt
