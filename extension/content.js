chrome.storage.local.get({IsEnabled : true}), ({IsEnabled}) => {
    toggleExtensionWork(IsEnabled);
});

chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.isEnabled) {
        toggleExtensionWork(changes.isEnabled.newValue);
    }
});

function toggleExtensionWork(isEnabled){
    if(IsEnabled){
        chrome.runtime.sendMessage({action : "STATE Changed", enabled : true});
        handleWorkerResponse()
    }
    else{
        chrome.runtime.sendMessage({action: "STATE Changed", enabled : false});
    }
}

chrome.runtime.onMessage((message, sender, sendResponse)) => {
    if (message == "Url have been blocked"){
        alertWindow();
    }
}


function alertWindow(){
    const isConfirmed = confirm("Цей URL є фішонговим. GUARD його заблоковав.\n Залишити його заблокваним?");

    if (!isConfirmed){
        chorme.runtime.sendMessage({action: "UNBLOCK URL"});
        alert("Розблоковую URL... ");
    }
    else{
        alert("Ви вирішили залишити його заблокованим.");
    }
}
