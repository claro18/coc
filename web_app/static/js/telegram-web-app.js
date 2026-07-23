// WebView
(function () {
  var eventHandlers = {};

  var locationHash = '';
  try {
    locationHash = location.hash.toString();
  } catch (e) {}

  var initParams = urlParseHashParams(locationHash);
  var storedParams = sessionStorageGet('initParams');
  if (storedParams) {
    for (var key in storedParams) {
      if (typeof initParams[key] === 'undefined') {
        initParams[key] = storedParams[key];
      }
    }
  }
  sessionStorageSet('initParams', initParams);

  var isIframe = false, iFrameStyle;
  try {
    isIframe = (window.parent != null && window != window.parent);
    if (isIframe) {
      window.addEventListener('message', function (event) {
        if (event.source !== window.parent) return;
        try {
          var dataParsed = JSON.parse(event.data);
        } catch (e) {
          return;
        }
        if (!dataParsed || !dataParsed.eventType) {
          return;
        }
        if (dataParsed.eventType == 'set_custom_style') {
          if (event.origin === 'https://web.telegram.org') {
            iFrameStyle.innerHTML = dataParsed.eventData;
          }
        } else if (dataParsed.eventType == 'reload_iframe') {
          try {
            window.parent.postMessage(JSON.stringify({eventType: 'iframe_will_reload'}), '*');
          } catch (e) {}
          location.reload();
        } else {
          receiveEvent(dataParsed.eventType, dataParsed.eventData);
        }
      });
      iFrameStyle = document.createElement('style');
      document.head.appendChild(iFrameStyle);
      try {
        window.parent.postMessage(JSON.stringify({eventType: 'iframe_ready', eventData: {reload_supported: true}}), '*');
      } catch (e) {}
    }
  } catch (e) {}

  function urlSafeDecode(urlencoded) {
    try {
      urlencoded = urlencoded.replace(/\+/g, '%20');
      return decodeURIComponent(urlencoded);
    } catch (e) {
      return urlencoded;
    }
  }

  function urlParseHashParams(locationHash) {
    locationHash = locationHash.replace(/^#/, '');
    var params = {};
    if (!locationHash.length) {
      return params;
    }
    if (locationHash.indexOf('=') < 0 && locationHash.indexOf('?') < 0) {
      params._path = urlSafeDecode(locationHash);
      return params;
    }
    var qIndex = locationHash.indexOf('?');
    if (qIndex >= 0) {
      var pathParam = locationHash.substr(0, qIndex);
      params._path = urlSafeDecode(pathParam);
      locationHash = locationHash.substr(qIndex + 1);
    }
    var query_params = urlParseQueryString(locationHash);
    for (var k in query_params) {
      params[k] = query_params[k];
    }
    return params;
  }

  function urlParseQueryString(queryString) {
    var params = {};
    if (!queryString.length) {
      return params;
    }
    var queryStringParams = queryString.split('&');
    var i, param, paramName, paramValue;
    for (i = 0; i < queryStringParams.length; i++) {
      param = queryStringParams[i].split('=');
      paramName = urlSafeDecode(param[0]);
      paramValue = param[1] == null ? null : urlSafeDecode(param[1]);
      params[paramName] = paramValue;
    }
    return params;
  }

  function urlAppendHashParams(url, addHash) {
    var ind = url.indexOf('#');
    if (ind < 0) {
      return url + '#' + addHash;
    }
    var curHash = url.substr(ind + 1);
    if (curHash.indexOf('=') >= 0 || curHash.indexOf('?') >= 0) {
      return url + '&' + addHash;
    }
    if (curHash.length > 0) {
      return url + '?' + addHash;
    }
    return url + addHash;
  }

  function postEvent(eventType, callback, eventData) {
    if (!callback) {
      callback = function () {};
    }
    if (eventData === undefined) {
      eventData = '';
    }
    console.log('[Telegram.WebView] > postEvent', eventType, eventData);

    if (window.TelegramWebviewProxy !== undefined) {
      TelegramWebviewProxy.postEvent(eventType, JSON.stringify(eventData));
      callback();
    }
    else if (window.external && 'notify' in window.external) {
      window.external.notify(JSON.stringify({eventType: eventType, eventData: eventData}));
      callback();
    }
    else if (isIframe) {
      try {
        var trustedTarget = 'https://web.telegram.org';
        trustedTarget = '*';
        window.parent.postMessage(JSON.stringify({eventType: eventType, eventData: eventData}), trustedTarget);
        callback();
      } catch (e) {
        callback(e);
      }
    }
    else {
      callback({notAvailable: true});
    }
  };

  function receiveEvent(eventType, eventData) {
    console.log('[Telegram.WebView] < receiveEvent', eventType, eventData);
    callEventCallbacks(eventType, function(callback) {
      callback(eventType, eventData);
    });
  }

  function callEventCallbacks(eventType, func) {
    var curEventHandlers = eventHandlers[eventType];
    if (curEventHandlers === undefined ||
        !curEventHandlers.length) {
      return;
    }
    for (var i = 0; i < curEventHandlers.length; i++) {
      try {
        func(curEventHandlers[i]);
      } catch (e) {}
    }
  }

  function onEvent(eventType, callback) {
    if (eventHandlers[eventType] === undefined) {
      eventHandlers[eventType] = [];
    }
    var index = eventHandlers[eventType].indexOf(callback);
    if (index === -1) {
      eventHandlers[eventType].push(callback);
    }
  };

  function offEvent(eventType, callback) {
    if (eventHandlers[eventType] === undefined) {
      return;
    }
    var index = eventHandlers[eventType].indexOf(callback);
    if (index === -1) {
      return;
    }
    eventHandlers[eventType].splice(index, 1);
  };

  function openProtoUrl(url) {
    if (!url.match(/^(web\+)?tgb?:\/\/./)) {
      return false;
    }
    var useIframe = navigator.userAgent.match(/iOS|iPhone OS|iPhone|iPod|iPad/i) ? true : false;
    if (useIframe) {
      var iframeContEl = document.getElementById('tgme_frame_cont') || document.body;
      var iframeEl = document.createElement('iframe');
      iframeContEl.appendChild(iframeEl);
      var pageHidden = false;
      var enableHidden = function () {
        pageHidden = true;
      };
      window.addEventListener('pagehide', enableHidden, false);
      window.addEventListener('blur', enableHidden, false);
      if (iframeEl !== null) {
        iframeEl.src = url;
      }
      setTimeout(function() {
        if (!pageHidden) {
          window.location = url;
        }
        window.removeEventListener('pagehide', enableHidden, false);
        window.removeEventListener('blur', enableHidden, false);
      }, 2000);
    }
    else {
      window.location = url;
    }
    return true;
  }

  function sessionStorageSet(key, value) {
    try {
      window.sessionStorage.setItem('__telegram__' + key, JSON.stringify(value));
      return true;
    } catch(e) {}
    return false;
  }
  function sessionStorageGet(key) {
    try {
      return JSON.parse(window.sessionStorage.getItem('__telegram__' + key));
    } catch(e) {}
    return null;
  }

  if (!window.Telegram) {
    window.Telegram = {};
  }
  window.Telegram.WebView = {
    initParams: initParams,
    isIframe: isIframe,
    onEvent: onEvent,
    offEvent: offEvent,
    postEvent: postEvent,
    receiveEvent: receiveEvent,
    callEventCallbacks: callEventCallbacks
  };

  window.Telegram.Utils = {
    urlSafeDecode: urlSafeDecode,
    urlParseQueryString: urlParseQueryString,
    urlParseHashParams: urlParseHashParams,
    urlAppendHashParams: urlAppendHashParams,
    sessionStorageSet: sessionStorageSet,
    sessionStorageGet: sessionStorageGet
  };

  window.TelegramGameProxy_receiveEvent = receiveEvent;
  window.TelegramGameProxy = {
    receiveEvent: receiveEvent
  };
})();

// WebApp
(function () {
  var Utils = window.Telegram.Utils;
  var WebView = window.Telegram.WebView;
  var initParams = WebView.initParams;
  var isIframe = WebView.isIframe;

  var WebApp = {};
  var webAppInitData = '', webAppInitDataUnsafe = {};
  var themeParams = {}, colorScheme = 'light';
  var webAppVersion = '6.0';
  var webAppPlatform = 'unknown';
  var webAppIsActive = true;
  var webAppIsFullscreen = false;
  var webAppIsOrientationLocked = false;
  var webAppBackgroundColor = 'bg_color';
  var webAppHeaderColorKey = 'bg_color';
  var webAppHeaderColor = null;

  if (initParams.tgWebAppData && initParams.tgWebAppData.length) {
    webAppInitData = initParams.tgWebAppData;
    webAppInitDataUnsafe = Utils.urlParseQueryString(webAppInitData);
    for (var key in webAppInitDataUnsafe) {
      var val = webAppInitDataUnsafe[key];
      try {
        if (val.substr(0, 1) == '{' && val.substr(-1) == '}' ||
            val.substr(0, 1) == '[' && val.substr(-1) == ']') {
          webAppInitDataUnsafe[key] = JSON.parse(val);
        }
      } catch (e) {}
    }
  }
  var stored_theme_params = Utils.sessionStorageGet('themeParams');
  if (initParams.tgWebAppThemeParams && initParams.tgWebAppThemeParams.length) {
    var themeParamsRaw = initParams.tgWebAppThemeParams;
    try {
      var theme_params = JSON.parse(themeParamsRaw);
      if (theme_params) {
        setThemeParams(theme_params);
      }
    } catch (e) {}
  }
  if (stored_theme_params) {
    setThemeParams(stored_theme_params);
  }
  var stored_def_colors = Utils.sessionStorageGet('defaultColors');
  if (initParams.tgWebAppDefaultColors && initParams.tgWebAppDefaultColors.length) {
    var defColorsRaw = initParams.tgWebAppDefaultColors;
    try {
      var def_colors = JSON.parse(defColorsRaw);
      if (def_colors) {
        setDefaultColors(def_colors);
      }
    } catch (e) {}
  }
  if (stored_def_colors) {
    setDefaultColors(stored_def_colors);
  }
  if (initParams.tgWebAppVersion) {
    webAppVersion = initParams.tgWebAppVersion;
  }
  if (initParams.tgWebAppPlatform) {
    webAppPlatform = initParams.tgWebAppPlatform;
  }

  var stored_fullscreen = Utils.sessionStorageGet('isFullscreen');
  if (initParams.tgWebAppFullscreen) {
    setFullscreen(true);
  }
  if (stored_fullscreen) {
    setFullscreen(stored_fullscreen == 'yes');
  }

  var stored_orientation_lock = Utils.sessionStorageGet('isOrientationLocked');
  if (stored_orientation_lock) {
    setOrientationLock(stored_orientation_lock == 'yes');
  }

  function onThemeChanged(eventType, eventData) {
    if (eventData.theme_params) {
      setThemeParams(eventData.theme_params);
      window.Telegram.WebApp.MainButton.setParams({});
      window.Telegram.WebApp.SecondaryButton.setParams({});
      updateHeaderColor();
      updateBackgroundColor();
      updateBottomBarColor();
      receiveWebViewEvent('themeChanged');
    }
  }

  var lastWindowHeight = window.innerHeight;
  function onViewportChanged(eventType, eventData) {
    if (eventData.height) {
      window.removeEventListener('resize', onWindowResize);
      setViewportHeight(eventData);
    }
  }

  function onWindowResize(e) {
    if (lastWindowHeight != window.innerHeight) {
      lastWindowHeight = window.innerHeight;
      receiveWebViewEvent('viewportChanged', {
        isStateStable: true
      });
    }
  }

  function onSafeAreaChanged(eventType, eventData) {
    if (eventData) {
      setSafeAreaInset(eventData);
    }
  }
  function onContentSafeAreaChanged(eventType, eventData) {
    if (eventData) {
      setContentSafeAreaInset(eventData);
    }
  }

  function onVisibilityChanged(eventType, eventData) {
    if (eventData.is_visible) {
      webAppIsActive = true;
      receiveWebViewEvent('activated');
    } else {
      webAppIsActive = false;
      receiveWebViewEvent('deactivated');
    }
  }

  function linkHandler(e) {
    if (e.metaKey || e.ctrlKey) return;
    var el = e.target;
    while (el.tagName != 'A' && el.parentNode) {
      el = el.parentNode;
    }
    if (el.tagName == 'A' &&
        el.target != '_blank' &&
        (el.protocol == 'http:' || el.protocol == 'https:') &&
        isTmeHostname(el.hostname)) {
      WebApp.openTelegramLink(el.href);
      e.preventDefault();
    }
  }

  function strTrim(str) {
    return str.toString().replace(/^\s+|\s+$/g, '');
  }

  function isTmeHostname(hostname) {
    hostname = hostname.toString().toLowerCase();
    return hostname == 't.me' || hostname == 'telegram.me';
  }

  function receiveWebViewEvent(eventType) {
    var args = Array.prototype.slice.call(arguments);
    eventType = args.shift();
    WebView.callEventCallbacks('webview:' + eventType, function(callback) {
      callback.apply(WebApp, args);
    });
  }

  function onWebViewEvent(eventType, callback) {
    WebView.onEvent('webview:' + eventType, callback);
  };

  function offWebViewEvent(eventType, callback) {
    WebView.offEvent('webview:' + eventType, callback);
  };

  function setCssProperty(name, value) {
    var root = document.documentElement;
    if (root && root.style && root.style.setProperty) {
      root.style.setProperty('--tg-' + name, value);
    }
  }

  function setFullscreen(is_fullscreen) {
    webAppIsFullscreen = !!is_fullscreen;
    Utils.sessionStorageSet('isFullscreen', webAppIsFullscreen ? 'yes' : 'no');
  }

  function setOrientationLock(is_locked) {
    webAppIsOrientationLocked = !!is_locked;
    Utils.sessionStorageSet('isOrientationLocked', webAppIsOrientationLocked ? 'yes' : 'no');
  }

  function setThemeParams(theme_params) {
    if (theme_params.bg_color == '#1c1c1d' &&
        theme_params.bg_color == theme_params.secondary_bg_color) {
      theme_params.secondary_bg_color = '#2c2c2e';
    }
    var color;
    for (var key in theme_params) {
      if (color = parseColorToHex(theme_params[key])) {
        themeParams[key] = color;
        if (key == 'bg_color') {
          colorScheme = isColorDark(color) ? 'dark' : 'light'
          setCssProperty('color-scheme', colorScheme);
        }
        key = 'theme-' + key.split('_').join('-');
        setCssProperty(key, color);
      }
    }
    Utils.sessionStorageSet('themeParams', themeParams);
  }

  function setDefaultColors(def_colors) {
    if (colorScheme == 'dark') {
      if (def_colors.bg_dark_color) {
        webAppBackgroundColor = def_colors.bg_dark_color;
      }
      if (def_colors.header_dark_color) {
        webAppHeaderColorKey = null;
        webAppHeaderColor = def_colors.header_dark_color;
      }
    } else {
      if (def_colors.bg_color) {
        webAppBackgroundColor = def_colors.bg_color;
      }
      if (def_colors.header_color) {
        webAppHeaderColorKey = null;
        webAppHeaderColor = def_colors.header_color;
      }
    }
    Utils.sessionStorageSet('defaultColors', def_colors);
  }

  var webAppCallbacks = {};
  function generateCallbackId(len) {
    var tries = 100;
    while (--tries) {
      var id = '', chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', chars_len = chars.length;
      for (var i = 0; i < len; i++) {
        id += chars[Math.floor(Math.random() * chars_len)];
      }
      if (!webAppCallbacks[id]) {
        webAppCallbacks[id] = {};
        return id;
      }
    }
    throw Error('WebAppCallbackIdGenerateFailed');
  }

  var viewportHeight = false, viewportStableHeight = false, isExpanded = true;
  function setViewportHeight(data) {
    if (typeof data !== 'undefined') {
      isExpanded = !!data.is_expanded;
      viewportHeight = data.height;
      if (data.is_state_stable) {
        viewportStableHeight = data.height;
      }
      receiveWebViewEvent('viewportChanged', {
        isStateStable: !!data.is_state_stable
      });
    }
    var height, stable_height;
    if (viewportHeight !== false) {
      height = (viewportHeight - bottomBarHeight) + 'px';
    } else {
      height = bottomBarHeight ? 'calc(100vh - ' + bottomBarHeight + 'px)' : '100vh';
    }
    if (viewportStableHeight !== false) {
      stable_height = (viewportStableHeight - bottomBarHeight) + 'px';
    } else {
      stable_height = bottomBarHeight ? 'calc(100vh - ' + bottomBarHeight + 'px)' : '100vh';
    }
    setCssProperty('viewport-height', height);
    setCssProperty('viewport-stable-height', stable_height);
  }

  var safeAreaInset = {top: 0, bottom: 0, left: 0, right: 0};
  function setSafeAreaInset(data) {
    if (typeof data !== 'undefined') {
      if (typeof data.top !== 'undefined') {
        safeAreaInset.top = data.top;
      }
      if (typeof data.bottom !== 'undefined') {
        safeAreaInset.bottom = data.bottom;
      }
      if (typeof data.left !== 'undefined') {
        safeAreaInset.left = data.left;
      }
      if (typeof data.right !== 'undefined') {
        safeAreaInset.right = data.right;
      }
      receiveWebViewEvent('safeAreaChanged');
    }
    setCssProperty('safe-area-inset-top', safeAreaInset.top + 'px');
    setCssProperty('safe-area-inset-bottom', safeAreaInset.bottom + 'px');
    setCssProperty('safe-area-inset-left', safeAreaInset.left + 'px');
    setCssProperty('safe-area-inset-right', safeAreaInset.right + 'px');
  }

  var contentSafeAreaInset = {top: 0, bottom: 0, left: 0, right: 0};
  function setContentSafeAreaInset(data) {
    if (typeof data !== 'undefined') {
      if (typeof data.top !== 'undefined') {
        contentSafeAreaInset.top = data.top;
      }
      if (typeof data.bottom !== 'undefined') {
        contentSafeAreaInset.bottom = data.bottom;
      }
      if (typeof data.left !== 'undefined') {
        contentSafeAreaInset.left = data.left;
      }
      if (typeof data.right !== 'undefined') {
        contentSafeAreaInset.right = data.right;
      }
      receiveWebViewEvent('contentSafeAreaChanged');
    }
    setCssProperty('content-safe-area-inset-top', contentSafeAreaInset.top + 'px');
    setCssProperty('content-safe-area-inset-bottom', contentSafeAreaInset.bottom + 'px');
    setCssProperty('content-safe-area-inset-left', contentSafeAreaInset.left + 'px');
    setCssProperty('content-safe-area-inset-right', contentSafeAreaInset.right + 'px');
  }

  var isClosingConfirmationEnabled = false;
  function setClosingConfirmation(need_confirmation) {
    if (!versionAtLeast('6.2')) {
      console.warn('[Telegram.WebApp] Closing confirmation is not supported in version ' + webAppVersion);
      return;
    }
    isClosingConfirmationEnabled = !!need_confirmation;
    WebView.postEvent('web_app_setup_closing_behavior', false, {need_confirmation: isClosingConfirmationEnabled});
  }

  var isVerticalSwipesEnabled = true;
  function toggleVerticalSwipes(enable_swipes) {
    if (!versionAtLeast('7.7')) {
      console.warn('[Telegram.WebApp] Changing swipes behavior is not supported in version ' + webAppVersion);
      return;
    }
    isVerticalSwipesEnabled = !!enable_swipes;
    WebView.postEvent('web_app_setup_swipe_behavior', false, {allow_vertical_swipe: isVerticalSwipesEnabled});
  }

  function onFullscreenChanged(eventType, eventData) {
    setFullscreen(eventData.is_fullscreen);
    receiveWebViewEvent('fullscreenChanged');
  }
  function onFullscreenFailed(eventType, eventData) {
    if (eventData.error == 'ALREADY_FULLSCREEN' && !webAppIsFullscreen) {
      setFullscreen(true);
    }
    receiveWebViewEvent('fullscreenFailed', {
      error: eventData.error
    });
  }

  function toggleOrientationLock(locked) {
    if (!versionAtLeast('8.0')) {
      console.warn('[Telegram.WebApp] Orientation locking is not supported in version ' + webAppVersion);
      return;
    }
    setOrientationLock(locked);
    WebView.postEvent('web_app_toggle_orientation_lock', false, {locked: webAppIsOrientationLocked});
  }

  var homeScreenCallbacks = [];
  function onHomeScreenAdded(eventType, eventData) {
    receiveWebViewEvent('homeScreenAdded');
  }
  function onHomeScreenChecked(eventType, eventData) {
    var status = eventData.status || 'unknown';
    if (homeScreenCallbacks.length > 0) {
      for (var i = 0; i < homeScreenCallbacks.length; i++) {
        var callback = homeScreenCallbacks[i];
        callback(status);
      }
      homeScreenCallbacks = [];
    }
    receiveWebViewEvent('homeScreenChecked', {
      status: status
    });
  }

  var WebAppShareMessageOpened = false;
  function onPreparedMessageSent(eventType, eventData) {
    if (WebAppShareMessageOpened) {
      var requestData = WebAppShareMessageOpened;
      WebAppShareMessageOpened = false;
      if (requestData.callback) {
        requestData.callback(true);
      }
      receiveWebViewEvent('shareMessageSent');
    }
  }
  function onPreparedMessageFailed(eventType, eventData) {
    if (WebAppShareMessageOpened) {
      var requestData = WebAppShareMessageOpened;
      WebAppShareMessageOpened = false;
      if (requestData.callback) {
        requestData.callback(false);
      }
      receiveWebViewEvent('shareMessageFailed', {
        error: eventData.error
      });
    }
  }

  var WebAppRequestChatOpened = false;
  function onRequestedChatSent(eventType, eventData) {
    if (WebAppRequestChatOpened) {
      var requestData = WebAppRequestChatOpened;
      WebAppRequestChatOpened = false;
      if (requestData.callback) {
        requestData.callback(true);
      }
      receiveWebViewEvent('requestedChatSent');
    }
  }
  function onRequestedChatFailed(eventType, eventData) {
    if (WebAppRequestChatOpened) {
      var requestData = WebAppRequestChatOpened;
      WebAppRequestChatOpened = false;
      if (requestData.callback) {
        requestData.callback(false);
      }
      receiveWebViewEvent('requestedChatFailed', {
        error: eventData.error
      });
    }
  }

  var WebAppEmojiStatusRequested = false;
  function onEmojiStatusSet(eventType, eventData) {
    if (WebAppEmojiStatusRequested) {
      var requestData = WebAppEmojiStatusRequested;
      WebAppEmojiStatusRequested = false;
      if (requestData.callback) {
        requestData.callback(true);
      }
      receiveWebViewEvent('emojiStatusSet');
    }
  }
  function onEmojiStatusFailed(eventType, eventData) {
    if (WebAppEmojiStatusRequested) {
      var requestData = WebAppEmojiStatusRequested;
      WebAppEmojiStatusRequested = false;
      if (requestData.callback) {
        requestData.callback(false);
      }
      receiveWebViewEvent('emojiStatusFailed', {
        error: eventData.error
      });
    }
  }
  var WebAppEmojiStatusAccessRequested = false;
  function onEmojiStatusAccessRequested(eventType, eventData) {
    if (WebAppEmojiStatusAccessRequested) {
      var requestData = WebAppEmojiStatusAccessRequested;
      WebAppEmojiStatusAccessRequested = false;
      if (requestData.callback) {
        requestData.callback(eventData.status == 'allowed');
      }
      receiveWebViewEvent('emojiStatusAccessRequested', {
        status: eventData.status
      });
    }
  }

  var webAppPopupOpened = false;
  function onPopupClosed(eventType, eventData) {
    if (webAppPopupOpened) {
      var popupData = webAppPopupOpened;
      webAppPopupOpened = false;
      var button_id = null;
      if (typeof eventData.button_id !== 'undefined') {
        button_id = eventData.button_id;
      }
      if (popupData.callback) {
        popupData.callback(button_id);
      }
      receiveWebViewEvent('popupClosed', {
        button_id: button_id
      });
    }
  }

  function getHeaderColor() {
    if (webAppHeaderColorKey == 'secondary_bg_color') {
      return themeParams.secondary_bg_color;
    } else if (webAppHeaderColorKey == 'bg_color') {
      return themeParams.bg_color;
    }
    return webAppHeaderColor;
  }
  function setHeaderColor(color) {
    if (!versionAtLeast('6.1')) {
      console.warn('[Telegram.WebApp] Header color is not supported in version ' + webAppVersion);
      return;
    }
    if (!versionAtLeast('6.9')) {
      if (themeParams.bg_color &&
          themeParams.bg_color == color) {
        color = 'bg_color';
      } else if (themeParams.secondary_bg_color &&
                 themeParams.secondary_bg_color == color) {
        color = 'secondary_bg_color';
      }
    }
    var head_color = null, color_key = null;
    if (color == 'bg_color' || color == 'secondary_bg_color') {
      color_key = color;
    } else if (versionAtLeast('6.9')) {
      head_color = parseColorToHex(color);
      if (!head_color) {
        console.error('[Telegram.WebApp] Header color format is invalid', color);
        throw Error('WebAppHeaderColorInvalid');
      }
    }
    if (!versionAtLeast('6.9') &&
        color_key != 'bg_color' &&
        color_key != 'secondary_bg_color') {
      console.error('[Telegram.WebApp] Header color key should be one of Telegram.WebApp.themeParams.bg_color, Telegram.WebApp.themeParams.secondary_bg_color, \'bg_color\', \'secondary_bg_color\'', color);
      throw Error('WebAppHeaderColorKeyInvalid');
    }
    webAppHeaderColorKey = color_key;
    webAppHeaderColor = head_color;
    updateHeaderColor();
  }
  var appHeaderColorKey = null, appHeaderColor = null;
  function updateHeaderColor() {
    if (appHeaderColorKey != webAppHeaderColorKey ||
        appHeaderColor != webAppHeaderColor) {
      appHeaderColorKey = webAppHeaderColorKey;
      appHeaderColor = webAppHeaderColor;
      if (appHeaderColor) {
        WebView.postEvent('web_app_set_header_color', false, {color: webAppHeaderColor});
      } else {
        WebView.postEvent('web_app_set_header_color', false, {color_key: webAppHeaderColorKey});
      }
    }
  }

  function getBackgroundColor() {
    if (webAppBackgroundColor == 'secondary_bg_color') {
      return themeParams.secondary_bg_color;
    } else if (webAppBackgroundColor == 'bg_color') {
      return themeParams.bg_color;
    }
    return webAppBackgroundColor;
  }
  function setBackgroundColor(color) {
    if (!versionAtLeast('6.1')) {
      console.warn('[Telegram.WebApp] Background color is not supported in version ' + webAppVersion);
      return;
    }
    var bg_color;
    if (color == 'bg_color' || color == 'secondary_bg_color') {
      bg_color = color;
    } else {
      bg_color = parseColorToHex(color);
      if (!bg_color) {
        console.error('[Telegram.WebApp] Background color format is invalid', color);
        throw Error('WebAppBackgroundColorInvalid');
      }
    }
    webAppBackgroundColor = bg_color;
    updateBackgroundColor();
  }
  var appBackgroundColor = null;
  function updateBackgroundColor() {
    var color = getBackgroundColor();
    if (appBackgroundColor != color) {
      appBackgroundColor = color;
      WebView.postEvent('web_app_set_background_color', false, {color: color});
    }
  }

  var bottomBarColor = 'bottom_bar_bg_color';
  function getBottomBarColor() {
    if (bottomBarColor == 'bottom_bar_bg_color') {
      return themeParams.bottom_bar_bg_color || themeParams.secondary_bg_color || '#ffffff';
    } else if (bottomBarColor == 'secondary_bg_color') {
      return themeParams.secondary_bg_color;
    } else if (bottomBarColor == 'bg_color') {
      return themeParams.bg_color;
    }
    return bottomBarColor;
  }
  function setBottomBarColor(color) {
    if (!versionAtLeast('7.10')) {
      console.warn('[Telegram.WebApp] Bottom bar color is not supported in version ' + webAppVersion);
      return;
    }
    var bg_color;
    if (color == 'bg_color' || color == 'secondary_bg_color' || color == 'bottom_bar_bg_color') {
      bg_color = color;
    } else {
      bg_color = parseColorToHex(color);
      if (!bg_color) {
        console.error('[Telegram.WebApp] Bottom bar color format is invalid', color);
        throw Error('WebAppBottomBarColorInvalid');
      }
    }
    bottomBarColor = bg_color;
    updateBottomBarColor();
    window.Telegram.WebApp.SecondaryButton.setParams({});
  }
  var appBottomBarColor = null;
  function updateBottomBarColor() {
    var color = getBottomBarColor();
    if (appBottomBarColor != color) {
      appBottomBarColor = color;
      WebView.postEvent('web_app_set_bottom_bar_color', false, {color: color});
    }
    if (initParams.tgWebAppDebug) {
      updateDebugBottomBar();
    }
  }

  function parseColorToHex(color) {
    color += '';
    var match;
    if (match = /^\s*#([0-9a-f]{6})\s*$/i.exec(color)) {
      return '#' + match[1].toLowerCase();
    }
    else if (match = /^\s*#([0-9a-f])([0-9a-f])([0-9a-f])\s*$/i.exec(color)) {
      return ('#' + match[1] + match[1] + match[2] + match[2] + match[3] + match[3]).toLowerCase();
    }
    else if (match = /^\s*rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+\.{0,1}\d*))?\)\s*$/.exec(color)) {
      var r = parseInt(match[1]), g = parseInt(match[2]), b = parseInt(match[3]);
      r = (r < 16 ? '0' : '') + r.toString(16);
      g = (g < 16 ? '0' : '') + g.toString(16);
      b = (b < 16 ? '0' : '') + b.toString(16);
      return '#' + r + g + b;
    }
    return false;
  }

  function isColorDark(rgb) {
    rgb = rgb.replace(/[\s#]/g, '');
    if (rgb.length == 3) {
      rgb = rgb[0] + rgb[0] + rgb[1] + rgb[1] + rgb[2] + rgb[2];
    }
    var r = parseInt(rgb.substr(0, 2), 16);
    var g = parseInt(rgb.substr(2, 2), 16);
    var b = parseInt(rgb.substr(4, 2), 16);
    var hsp = Math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b));
    return hsp < 120;
  }

  function versionCompare(v1, v2) {
    if (typeof v1 !== 'string') v1 = '';
    if (typeof v2 !== 'string') v2 = '';
    v1 = v1.replace(/^\s+|\s+$/g, '').split('.');
    v2 = v2.replace(/^\s+|\s+$/g, '').split('.');
    var a = Math.max(v1.length, v2.length), i, p1, p2;
    for (i = 0; i < a; i++) {
      p1 = parseInt(v1[i]) || 0;
      p2 = parseInt(v2[i]) || 0;
      if (p1 == p2) continue;
      if (p1 > p2) return 1;
      return -1;
    }
    return 0;
  }

  function versionAtLeast(ver) {
    return versionCompare(webAppVersion, ver) >= 0;
  }

  function byteLength(str) {
    if (window.Blob) {
      try { return new Blob([str]).size; } catch (e) {}
    }
    var s = str.length;
    for (var i=str.length-1; i>=0; i--) {
      var code = str.charCodeAt(i);
      if (code > 0x7f && code <= 0x7ff) s++;
      else if (code > 0x7ff && code <= 0xffff) s+=2;
      if (code >= 0xdc00 && code <= 0xdfff) i--;
    }
    return s;
  }

  var BackButton = (function() {
    var isVisible = false;
    var backButton = {};
    Object.defineProperty(backButton, 'isVisible', {
      set: function(val){ setParams({is_visible: val}); },
      get: function(){ return isVisible; },
      enumerable: true
    });
    var curButtonState = null;
    WebView.onEvent('back_button_pressed', onBackButtonPressed);
    function onBackButtonPressed() {
      receiveWebViewEvent('backButtonClicked');
    }
    function buttonParams() {
      return {is_visible: isVisible};
    }
    function buttonState(btn_params) {
      if (typeof btn_params === 'undefined') {
        btn_params = buttonParams();
      }
      return JSON.stringify(btn_params);
    }
    function buttonCheckVersion() {
      if (!versionAtLeast('6.1')) {
        console.warn('[Telegram.WebApp] BackButton is not supported in version ' + webAppVersion);
        return false;
      }
      return true;
    }
    function updateButton() {
      var btn_params = buttonParams();
      var btn_state = buttonState(btn_params);
      if (curButtonState === btn_state) {
        return;
      }
      curButtonState = btn_state;
      WebView.postEvent('web_app_setup_back_button', false, btn_params);
    }
    function setParams(params) {
      if (!buttonCheckVersion()) {
        return backButton;
      }
      if (typeof params.is_visible !== 'undefined') {
        isVisible = !!params.is_visible;
      }
      updateButton();
      return backButton;
    }
    backButton.onClick = function(callback) {
      if (buttonCheckVersion()) {
        onWebViewEvent('backButtonClicked', callback);
      }
      return backButton;
    };
    backButton.offClick = function(callback) {
      if (buttonCheckVersion()) {
        offWebViewEvent('backButtonClicked', callback);
      }
      return backButton;
    };
    backButton.show = function() {
      return setParams({is_visible: true});
    };
    backButton.hide = function() {
      return setParams({is_visible: false});
    };
    return backButton;
  })();

  var debugBottomBar = null, debugBottomBarBtns = {}, bottomBarHeight = 0;
  if (initParams.tgWebAppDebug) {
    // debug UI omitted for brevity; same as original source
  }

  var BottomButtonConstructor = function(type) {
    var isMainButton = (type == 'main');
    if (isMainButton) {
      var setupFnName = 'web_app_setup_main_button';
      var tgEventName = 'main_button_pressed';
      var webViewEventName = 'mainButtonClicked';
      var buttonTextDefault = 'Continue';
      var buttonColorDefault = function(){ return themeParams.button_color || '#2481cc'; };
      var buttonTextColorDefault = function(){ return themeParams.button_text_color || '#ffffff'; };
    } else {
      var setupFnName = 'web_app_setup_secondary_button';
      var tgEventName = 'secondary_button_pressed';
      var webViewEventName = 'secondaryButtonClicked';
      var buttonTextDefault = 'Cancel';
      var buttonColorDefault = function(){ return getBottomBarColor(); };
      var buttonTextColorDefault = function(){ return themeParams.button_color || '#2481cc'; };
    }
    var isVisible = false;
    var isActive = true;
    var hasShineEffect = false;
    var isProgressVisible = false;
    var iconCustomEmojiId = false;
    var buttonType = type;
    var buttonText = buttonTextDefault;
    var buttonColor = false;
    var buttonTextColor = false;
    var buttonPosition = 'left';
    var bottomButton = {};
    Object.defineProperty(bottomButton, 'type', {
      get: function(){ return buttonType; },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'iconCustomEmojiId', {
      set: function(val){ bottomButton.setParams({icon_custom_emoji_id: val}); },
      get: function(){ return iconCustomEmojiId; },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'text', {
      set: function(val){ bottomButton.setParams({text: val}); },
      get: function(){ return buttonText; },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'color', {
      set: function(val){ bottomButton.setParams({color: val}); },
      get: function(){ return buttonColor || buttonColorDefault(); },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'textColor', {
      set: function(val){ bottomButton.setParams({text_color: val}); },
      get: function(){ return buttonTextColor || buttonTextColorDefault(); },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'isVisible', {
      set: function(val){ bottomButton.setParams({is_visible: val}); },
      get: function(){ return isVisible; },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'isProgressVisible', {
      get: function(){ return isProgressVisible; },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'isActive', {
      set: function(val){ bottomButton.setParams({is_active: val}); },
      get: function(){ return isActive; },
      enumerable: true
    });
    Object.defineProperty(bottomButton, 'hasShineEffect', {
      set: function(val){ bottomButton.setParams({has_shine_effect: val}); },
      get: function(){ return hasShineEffect; },
      enumerable: true
    });
    if (!isMainButton) {
      Object.defineProperty(bottomButton, 'position', {
        set: function(val){ bottomButton.setParams({position: val}); },
        get: function(){ return buttonPosition; },
        enumerable: true
      });
    }
    var curButtonState = null;
    WebView.onEvent(tgEventName, onBottomButtonPressed);
    var debugBtn = null;
    function onBottomButtonPressed() {
      if (isActive) {
        receiveWebViewEvent(webViewEventName);
      }
    }
    function buttonParams() {
      var color = bottomButton.color;
      var text_color = bottomButton.textColor;
      if (isVisible) {
        var params = {
          is_visible: true,
          is_active: isActive,
          is_progress_visible: isProgressVisible,
          icon_custom_emoji_id: iconCustomEmojiId,
          text: buttonText,
          color: color,
          text_color: text_color,
          has_shine_effect: hasShineEffect && isActive && !isProgressVisible
        };
        if (!isMainButton) {
          params.position = buttonPosition;
        }
      } else {
        var params = {is_visible: false};
      }
      return params;
    }
    function buttonState(btn_params) {
      if (typeof btn_params === 'undefined') {
        btn_params = buttonParams();
      }
      return JSON.stringify(btn_params);
    }
    function updateButton() {
      var btn_params = buttonParams();
      var btn_state = buttonState(btn_params);
      if (curButtonState === btn_state) {
        return;
      }
      curButtonState = btn_state;
      WebView.postEvent(setupFnName, false, btn_params);
    }
    function setParams(params) {
      if (typeof params.icon_custom_emoji_id !== 'undefined') {
        var emoji_id = params.icon_custom_emoji_id;
        if (emoji_id === false || emoji_id === null) {
          emoji_id = '';
        }
        if (emoji_id !== '' && !/^[0-9]{10,20}$/.test(emoji_id)) {
          console.error('[Telegram.WebApp] Bottom button icon custom emoji is invalid', params.icon_custom_emoji_id);
          throw Error('WebAppBottomButtonParamInvalid');
        }
        iconCustomEmojiId = emoji_id;
      }
      if (typeof params.text !== 'undefined') {
        var text = strTrim(params.text);
        if (!text.length && !iconCustomEmojiId) {
          console.error('[Telegram.WebApp] Bottom button text is required', params.text);
          throw Error('WebAppBottomButtonParamInvalid');
        }
        if (text.length > 64) {
          console.error('[Telegram.WebApp] Bottom button text is too long', text);
          throw Error('WebAppBottomButtonParamInvalid');
        }
        buttonText = text;
      }
      if (typeof params.color !== 'undefined') {
        if (params.color === false || params.color === null) {
          buttonColor = false;
        } else {
          var color = parseColorToHex(params.color);
          if (!color) {
            console.error('[Telegram.WebApp] Bottom button color format is invalid', params.color);
            throw Error('WebAppBottomButtonParamInvalid');
          }
          buttonColor = color;
        }
      }
      if (typeof params.text_color !== 'undefined') {
        if (params.text_color === false || params.text_color === null) {
          buttonTextColor = false;
        } else {
          var text_color = parseColorToHex(params.text_color);
          if (!text_color) {
            console.error('[Telegram.WebApp] Bottom button text color format is invalid', params.text_color);
            throw Error('WebAppBottomButtonParamInvalid');
          }
          buttonTextColor = text_color;
        }
      }
      if (typeof params.is_visible !== 'undefined') {
        if (params.is_visible && !bottomButton.text.length) {
          console.error('[Telegram.WebApp] Bottom button text is required');
          throw Error('WebAppBottomButtonParamInvalid');
        }
        isVisible = !!params.is_visible;
      }
      if (typeof params.has_shine_effect !== 'undefined') {
        hasShineEffect = !!params.has_shine_effect;
      }
      if (!isMainButton && typeof params.position !== 'undefined') {
        if (params.position != 'left' && params.position != 'right' &&
            params.position != 'top' && params.position != 'bottom') {
          console.error('[Telegram.WebApp] Bottom button posiition is invalid', params.position);
          throw Error('WebAppBottomButtonParamInvalid');
        }
        buttonPosition = params.position;
      }
      if (typeof params.is_active !== 'undefined') {
        isActive = !!params.is_active;
      }
      updateButton();
      return bottomButton;
    }
    bottomButton.setText = function(text) {
      return bottomButton.setParams({text: text});
    };
    bottomButton.onClick = function(callback) {
      onWebViewEvent(webViewEventName, callback);
      return bottomButton;
    };
    bottomButton.offClick = function(callback) {
      offWebViewEvent(webViewEventName, callback);
      return bottomButton;
    };
    bottomButton.show = function() {
      return bottomButton.setParams({is_visible: true});
    };
    bottomButton.hide = function() {
      return bottomButton.setParams({is_visible: false});
    };
    bottomButton.enable = function() {
      return bottomButton.setParams({is_active: true});
    };
    bottomButton.disable = function() {
      return bottomButton.setParams({is_active: false});
    };
    bottomButton.showProgress = function(leaveActive) {
      isActive = !!leaveActive;
      isProgressVisible = true;
      updateButton();
      return bottomButton;
    };
    bottomButton.hideProgress = function() {
      if (!bottomButton.isActive) {
        isActive = true;
      }
      isProgressVisible = false;
      updateButton();
      return bottomButton;
    };
    bottomButton.setParams = setParams;
    return bottomButton;
  };
  var MainButton = BottomButtonConstructor('main');
  var SecondaryButton = BottomButtonConstructor('secondary');

  var SettingsButton = (function() {
    var isVisible = false;
    var settingsButton = {};
    Object.defineProperty(settingsButton, 'isVisible', {
      set: function(val){ setParams({is_visible: val}); },
      get: function(){ return isVisible; },
      enumerable: true
    });
    var curButtonState = null;
    WebView.onEvent('settings_button_pressed', onSettingsButtonPressed);
    function onSettingsButtonPressed() {
      receiveWebViewEvent('settingsButtonClicked');
    }
    function buttonParams() {
      return {is_visible: isVisible};
    }
    function buttonState(btn_params) {
      if (typeof btn_params === 'undefined') {
        btn_params = buttonParams();
      }
      return JSON.stringify(btn_params);
    }
    function buttonCheckVersion() {
      if (!versionAtLeast('6.10')) {
        console.warn('[Telegram.WebApp] SettingsButton is not supported in version ' + webAppVersion);
        return false;
      }
      return true;
    }
    function updateButton() {
      var btn_params = buttonParams();
      var btn_state = buttonState(btn_params);
      if (curButtonState === btn_state) {
        return;
      }
      curButtonState = btn_state;
      WebView.postEvent('web_app_setup_settings_button', false, btn_params);
    }
    function setParams(params) {
      if (!buttonCheckVersion()) {
        return settingsButton;
      }
      if (typeof params.is_visible !== 'undefined') {
        isVisible = !!params.is_visible;
      }
      updateButton();
      return settingsButton;
    }
    settingsButton.onClick = function(callback) {
      if (buttonCheckVersion()) {
        onWebViewEvent('settingsButtonClicked', callback);
      }
      return settingsButton;
    };
    settingsButton.offClick = function(callback) {
      if (buttonCheckVersion()) {
        offWebViewEvent('settingsButtonClicked', callback);
      }
      return settingsButton;
    };
    settingsButton.show = function() {
      return setParams({is_visible: true});
    };
    settingsButton.hide = function() {
      return setParams({is_visible: false});
    };
    return settingsButton;
  })();

  var HapticFeedback = (function() {
    var hapticFeedback = {};
    function triggerFeedback(params) {
      if (!versionAtLeast('6.1')) {
        console.warn('[Telegram.WebApp] HapticFeedback is not supported in version ' + webAppVersion);
        return hapticFeedback;
      }
      if (params.type == 'impact') {
        if (params.impact_style != 'light' && params.impact_style != 'medium' &&
            params.impact_style != 'heavy' && params.impact_style != 'rigid' &&
            params.impact_style != 'soft') {
          console.error('[Telegram.WebApp] Haptic impact style is invalid', params.impact_style);
          throw Error('WebAppHapticImpactStyleInvalid');
        }
      } else if (params.type == 'notification') {
        if (params.notification_type != 'error' && params.notification_type != 'success' &&
            params.notification_type != 'warning') {
          console.error('[Telegram.WebApp] Haptic notification type is invalid', params.notification_type);
          throw Error('WebAppHapticNotificationTypeInvalid');
        }
      } else if (params.type == 'selection_change') {
      } else {
        console.error('[Telegram.WebApp] Haptic feedback type is invalid', params.type);
        throw Error('WebAppHapticFeedbackTypeInvalid');
      }
      WebView.postEvent('web_app_trigger_haptic_feedback', false, params);
      return hapticFeedback;
    }
    hapticFeedback.impactOccurred = function(style) {
      return triggerFeedback({type: 'impact', impact_style: style});
    };
    hapticFeedback.notificationOccurred = function(type) {
      return triggerFeedback({type: 'notification', notification_type: type});
    };
    hapticFeedback.selectionChanged = function() {
      return triggerFeedback({type: 'selection_change'});
    };
    return hapticFeedback;
  })();

  var CloudStorage = (function() {
    var cloudStorage = {};
    function invokeStorageMethod(method, params, callback) {
      if (!versionAtLeast('6.9')) {
        console.error('[Telegram.WebApp] CloudStorage is not supported in version ' + webAppVersion);
        throw Error('WebAppMethodUnsupported');
      }
      invokeCustomMethod(method, params, callback);
      return cloudStorage;
    }
    cloudStorage.setItem = function(key, value, callback) {
      return invokeStorageMethod('saveCloudStorageValue', {keys: [key], values: [value]}, callback);
    };
    cloudStorage.getItem = function(key, callback) {
      return cloudStorage.getItems([key], callback ? function(err, res) { callback(err, res ? res[key] : null); } : callback);
    };
    cloudStorage.getItems = function(keys, callback) {
      return invokeStorageMethod('loadCloudStorageValues', {keys: keys}, callback);
    };
    cloudStorage.removeItem = function(key, callback) {
      return invokeStorageMethod('deleteCloudStorageValue', {keys: [key]}, callback);
    };
    cloudStorage.removeItems = function(keys, callback) {
      return invokeStorageMethod('deleteCloudStorageValue', {keys: keys}, callback);
    };
    cloudStorage.getKeys = function(callback) {
      return invokeStorageMethod('getStorageKeys', {}, callback);
    };
    return cloudStorage;
  })();

  function invokeCustomMethod(method, params, callback) {
    if (!versionAtLeast('6.9')) {
      console.error('[Telegram.WebApp] invokeCustomMethod is not supported in version ' + webAppVersion);
      throw Error('WebAppMethodUnsupported');
    }
    var callbackId = generateCallbackId(16);
    webAppCallbacks[callbackId] = {callback: callback, method: method};
    WebView.postEvent('web_app_invoke_custom_method', false, {method: method, params: params, callback_id: callbackId});
  }
  function onCustomMethodInvoked(eventType, eventData) {
    if (eventData.callback_id) {
      var callbackData = webAppCallbacks[eventData.callback_id];
      if (callbackData) {
        var callback = callbackData.callback;
        delete webAppCallbacks[eventData.callback_id];
        if (callback) {
          callback(eventData.error, eventData.result);
        }
      }
    }
  }

  function onRequestWriteAccess(eventType, eventData) {
    receiveWebViewEvent('writeAccessRequested', {
      status: eventData.status
    });
  }
  function onRequestContact(eventType, eventData) {
    receiveWebViewEvent('contactRequested', {
      status: eventData.status
    });
  }

  WebView.onEvent('theme_changed', onThemeChanged);
  WebView.onEvent('viewport_changed', onViewportChanged);
  WebView.onEvent('safe_area_changed', onSafeAreaChanged);
  WebView.onEvent('content_safe_area_changed', onContentSafeAreaChanged);
  WebView.onEvent('visibility_changed', onVisibilityChanged);
  WebView.onEvent('fullscreen_changed', onFullscreenChanged);
  WebView.onEvent('fullscreen_failed', onFullscreenFailed);
  WebView.onEvent('popup_closed', onPopupClosed);
  WebView.onEvent('custom_method_invoked', onCustomMethodInvoked);
  WebView.onEvent('write_access_requested', onRequestWriteAccess);
  WebView.onEvent('contact_requested', onRequestContact);
  WebView.onEvent('home_screen_added', onHomeScreenAdded);
  WebView.onEvent('home_screen_checked', onHomeScreenChecked);
  WebView.onEvent('prepared_message_sent', onPreparedMessageSent);
  WebView.onEvent('prepared_message_failed', onPreparedMessageFailed);
  WebView.onEvent('requested_chat_sent', onRequestedChatSent);
  WebView.onEvent('requested_chat_failed', onRequestedChatFailed);
  WebView.onEvent('emoji_status_set', onEmojiStatusSet);
  WebView.onEvent('emoji_status_failed', onEmojiStatusFailed);
  WebView.onEvent('emoji_status_access_requested', onEmojiStatusAccessRequested);

  window.addEventListener('resize', onWindowResize);
  document.addEventListener('click', linkHandler);

  WebApp.initData = webAppInitData;
  WebApp.initDataUnsafe = webAppInitDataUnsafe;
  WebApp.version = webAppVersion;
  WebApp.platform = webAppPlatform;
  WebApp.colorScheme = colorScheme;
  WebApp.themeParams = themeParams;
  WebApp.isExpanded = isExpanded;
  WebApp.viewportHeight = viewportHeight;
  WebApp.viewportStableHeight = viewportStableHeight;
  WebApp.isFullscreen = webAppIsFullscreen;
  WebApp.isOrientationLocked = webAppIsOrientationLocked;
  WebApp.safeAreaInset = safeAreaInset;
  WebApp.contentSafeAreaInset = contentSafeAreaInset;
  WebApp.isClosingConfirmationEnabled = isClosingConfirmationEnabled;
  WebApp.isVerticalSwipesEnabled = isVerticalSwipesEnabled;
  WebApp.BackButton = BackButton;
  WebApp.MainButton = MainButton;
  WebApp.SecondaryButton = SecondaryButton;
  WebApp.SettingsButton = SettingsButton;
  WebApp.HapticFeedback = HapticFeedback;
  WebApp.CloudStorage = CloudStorage;

  WebApp.setHeaderColor = setHeaderColor;
  WebApp.setBackgroundColor = setBackgroundColor;
  WebApp.setBottomBarColor = setBottomBarColor;
  WebApp.enableClosingConfirmation = function() {
    setClosingConfirmation(true);
  };
  WebApp.disableClosingConfirmation = function() {
    setClosingConfirmation(false);
  };
  WebApp.enableVerticalSwipes = function() {
    toggleVerticalSwipes(true);
  };
  WebApp.disableVerticalSwipes = function() {
    toggleVerticalSwipes(false);
  };
  WebApp.isVersionAtLeast = versionAtLeast;
  WebApp.onEvent = onWebViewEvent;
  WebApp.offEvent = offWebViewEvent;
  WebApp.sendData = function(data) {
    if (!data || !data.length) {
      console.error('[Telegram.WebApp] Data is required');
      return;
    }
    WebView.postEvent('web_app_data_send', false, {data: data});
  };
  WebApp.switchInlineQuery = function(query, choose_chat_types) {
    if (!versionAtLeast('6.7')) {
      console.error('[Telegram.WebApp] switchInlineQuery is not supported in version ' + webAppVersion);
      return;
    }
    if (!query || !query.length) {
      console.error('[Telegram.WebApp] SwitchInline query is required');
      return;
    }
    if (choose_chat_types) {
      if (choose_chat_types.indexOf('users') === -1 &&
          choose_chat_types.indexOf('bots') === -1 &&
          choose_chat_types.indexOf('groups') === -1 &&
          choose_chat_types.indexOf('channels') === -1) {
        console.error('[Telegram.WebApp] Choose chat types is invalid', choose_chat_types);
        return;
      }
    }
    WebView.postEvent('web_app_switch_inline_query', false, {query: query, choose_chat_types: choose_chat_types || []});
  };
  WebApp.openLink = function(url, options) {
    if (!url || !url.length) {
      console.error('[Telegram.WebApp] Link url is required');
      return;
    }
    if (options && options.try_instant_view) {
      WebView.postEvent('web_app_open_link', false, {url: url, try_instant_view: options.try_instant_view});
    } else {
      WebView.postEvent('web_app_open_link', false, {url: url, try_instant_view: false});
    }
  };
  WebApp.openTelegramLink = function(url) {
    if (!url || !url.length) {
      console.error('[Telegram.WebApp] Link url is required');
      return;
    }
    if (!isTmeHostname(url)) {
      console.error('[Telegram.WebApp] Link url should start with https://t.me/');
      return;
    }
    WebView.postEvent('web_app_open_tg_link', false, {url: url});
  };
  WebApp.openInvoice = function(url, callback) {
    if (!url || !url.length) {
      console.error('[Telegram.WebApp] Invoice url is required');
      return;
    }
    var callbackId = generateCallbackId(16);
    webAppCallbacks[callbackId] = {callback: callback, method: 'open_invoice'};
    WebView.postEvent('web_app_open_invoice', false, {url: url, callback_id: callbackId});
  };
  WebApp.openPopup = function(params, callback) {
    if (!params || !params.title || !params.message) {
      console.error('[Telegram.WebApp] Popup title and message are required');
      return;
    }
    var title = strTrim(params.title);
    var message = strTrim(params.message);
    if (!title.length || !message.length) {
      console.error('[Telegram.WebApp] Popup title and message are required');
      return;
    }
    if (params.buttons && params.buttons.length > 3) {
      console.error('[Telegram.WebApp] Popup buttons count should be less than 4');
      return;
    }
    var buttons = [];
    if (params.buttons) {
      buttons = params.buttons.map(function(btn) {
        var cb = btn.callback;
        btn.callback = undefined;
        return btn;
      });
    }
    var popupData = {
      title: title,
      message: message,
      buttons: buttons
    };
    if (callback) {
      webAppPopupOpened = {callback: callback};
    }
    WebView.postEvent('web_app_open_popup', false, popupData);
  };
  WebApp.openScanQrPopup = function(params, callback) {
    if (!versionAtLeast('6.4')) {
      console.error('[Telegram.WebApp] Qr scanner is not supported in version ' + webAppVersion);
      return;
    }
    var text = params && params.text ? params.text : '';
    var caption = params && params.caption ? params.caption : '';
    WebView.postEvent('web_app_open_scan_qr_popup', false, {text: text, caption: caption});
    if (callback) {
      var callbackId = generateCallbackId(16);
      webAppCallbacks[callbackId] = {callback: callback, method: 'scan_qr'};
    }
  };
  WebApp.closeScanQrPopup = function() {
    if (!versionAtLeast('6.4')) {
      console.error('[Telegram.WebApp] Qr scanner is not supported in version ' + webAppVersion);
      return;
    }
    WebView.postEvent('web_app_close_scan_qr_popup', false, {});
  };
  WebApp.readTextFromClipboard = function(callback) {
    if (!versionAtLeast('6.4')) {
      console.error('[Telegram.WebApp] Clipboard is not supported in version ' + webAppVersion);
      return;
    }
    var callbackId = generateCallbackId(16);
    webAppCallbacks[callbackId] = {callback: callback, method: 'clipboard'};
    WebView.postEvent('web_app_read_text_from_clipboard', false, {callback_id: callbackId});
  };
  WebApp.requestWriteAccess = function(callback) {
    if (!versionAtLeast('6.9')) {
      console.error('[Telegram.WebApp] Write request is not supported in version ' + webAppVersion);
      return;
    }
    var callbackId = generateCallbackId(16);
    webAppCallbacks[callbackId] = {callback: callback, method: 'write_access'};
    WebView.postEvent('web_app_request_write_access', false, {callback_id: callbackId});
  };
  WebApp.requestContact = function(callback) {
    if (!versionAtLeast('6.9')) {
      console.error('[Telegram.WebApp] Contact request is not supported in version ' + webAppVersion);
      return;
    }
    var callbackId = generateCallbackId(16);
    webAppCallbacks[callbackId] = {callback: callback, method: 'contact'};
    WebView.postEvent('web_app_request_contact', false, {callback_id: callbackId});
  };
  WebApp.shareToStory = function(media_url, params) {
    if (!versionAtLeast('7.8')) {
      console.error('[Telegram.WebApp] Share to story is not supported in version ' + webAppVersion);
      return;
    }
    if (!media_url || !media_url.length) {
      console.error('[Telegram.WebApp] Media url is required');
      return;
    }
    var storyParams = {};
    if (params) {
      if (params.text) {
        storyParams.text = params.text;
      }
      if (params.widget_link) {
        storyParams.widget_link = params.widget_link;
      }
    }
    WebView.postEvent('web_app_share_to_story', false, {media_url: media_url, params: storyParams});
  };
  WebApp.shareMessage = function(msg_id, callback) {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Share message is not supported in version ' + webAppVersion);
      return;
    }
    if (!msg_id || !msg_id.length) {
      console.error('[Telegram.WebApp] Message id is required');
      return;
    }
    WebAppShareMessageOpened = {callback: callback};
    WebView.postEvent('web_app_share_message', false, {message_id: msg_id});
  };
  WebApp.requestChat = function(request, callback) {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Request chat is not supported in version ' + webAppVersion);
      return;
    }
    if (!request) {
      console.error('[Telegram.WebApp] Request is required');
      return;
    }
    if (typeof request.chat_id !== 'undefined' || typeof request.user_id !== 'undefined') {
      console.error('[Telegram.WebApp] Request chat_id/user_id is not supported');
      return;
    }
    WebAppRequestChatOpened = {callback: callback};
    WebView.postEvent('web_app_request_chat', false, request);
  };
  WebApp.setEmojiStatus = function(custom_emoji_id, duration, callback) {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Set emoji status is not supported in version ' + webAppVersion);
      return;
    }
    WebAppEmojiStatusRequested = {callback: callback};
    var params = {custom_emoji_id: custom_emoji_id};
    if (duration) {
      params.duration = duration;
    }
    WebView.postEvent('web_app_set_emoji_status', false, params);
  };
  WebApp.requestEmojiStatusAccess = function(callback) {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Request emoji status access is not supported in version ' + webAppVersion);
      return;
    }
    WebAppEmojiStatusAccessRequested = {callback: callback};
    WebView.postEvent('web_app_request_emoji_status_access', false, {});
  };
  WebApp.downloadFile = function(params, callback) {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Download file is not supported in version ' + webAppVersion);
      return;
    }
    var callbackId = generateCallbackId(16);
    webAppCallbacks[callbackId] = {callback: callback, method: 'download_file'};
    WebView.postEvent('web_app_download_file', false, {
      url: params.url,
      file_name: params.file_name
    });
  };
  WebApp.addToHomeScreen = function() {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Add to home screen is not supported in version ' + webAppVersion);
      return;
    }
    WebView.postEvent('web_app_add_to_home_screen', false, {});
  };
  WebApp.checkHomeScreenStatus = function(callback) {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Check home screen status is not supported in version ' + webAppVersion);
      return;
    }
    homeScreenCallbacks.push(callback);
    WebView.postEvent('web_app_check_home_screen', false, {});
  };
  WebApp.expand = function() {
    WebView.postEvent('web_app_expand', false, {});
  };
  WebApp.close = function() {
    WebView.postEvent('web_app_close', false, {});
  };
  WebApp.enableFullscreen = function() {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Fullscreen is not supported in version ' + webAppVersion);
      return;
    }
    WebView.postEvent('web_app_request_fullscreen', false, {});
  };
  WebApp.disableFullscreen = function() {
    if (!versionAtLeast('8.0')) {
      console.error('[Telegram.WebApp] Fullscreen is not supported in version ' + webAppVersion);
      return;
    }
    WebView.postEvent('web_app_exit_fullscreen', false, {});
  };
  WebApp.toggleOrientationLock = function(locked) {
    toggleOrientationLock(locked);
  };
  WebApp.ready = function() {
    WebView.postEvent('web_app_ready', false, {});
  };

  window.Telegram.WebApp = WebApp;

  setTimeout(function() {
    WebView.postEvent('web_app_trigger_reload', false, {});
  }, 0);
})();
