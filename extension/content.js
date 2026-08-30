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

