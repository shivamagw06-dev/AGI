export function analyticsClientInfo(ua='') {
 const browser=/Edg\//.test(ua)?'Edge':/OPR\//.test(ua)?'Opera':/Firefox\//.test(ua)?'Firefox':/SamsungBrowser\//.test(ua)?'Samsung Internet':/Chrome\/|CriOS\//.test(ua)?'Chrome':/Safari\//.test(ua)?'Safari':'Other';
 const os=/iPhone|iPad|iPod/.test(ua)?'iOS':/Android/.test(ua)?'Android':/Windows/.test(ua)?'Windows':/Macintosh|Mac OS X/.test(ua)?'macOS':/Linux/.test(ua)?'Linux':'Other';
 return {browser,os};
}
