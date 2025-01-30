/* The tabs which we process here, not in the list will be ignored */
const allTabs = [
  'summary',
  'validity',
  'accuracy',
  'usefulness',
  'additional-fields',
  'conversion-errors',
  'upload',
  'link',
  'paste'
];

(function () {
  /* tab switching mechanism <a href='#link'> -> click handler > */

  /* Find all the <a href="#tab"> Links */
  for (const tab of allTabs) {
    /* For each type (e.g. 'paste') add a click handler and set state */
    for (const tabLink of document.querySelectorAll(`a[href="#${tab}"]`)) {
      tabLink.addEventListener('click', (event) => {
        event.preventDefault();
        /* We do this manually to avoid page jumping position to the href/id */
        window.location.hash = `#${tab}`;

        /* Remove active from all tabs */
        for (const otherTabs of document.getElementsByClassName('tab')) {
          otherTabs.classList.remove('tab--active');
        }
        /* Add active to our tab */
        document.getElementById(`${tab}-tab-link`).parentElement.classList.toggle('tab--active');

        for (const tabContents of document.getElementsByClassName('tab-content')) {
          tabContents.setAttribute('style', 'display:none');
        }

        document.getElementById(`${tab}-tab`).setAttribute('style', 'display: block');
      });
    }
  }
})();

(function () {
  /* If "?open-all=true" is passed show all tabs on the page at once
    and ignore any resuming of the tab state.
  */
  const params = new URLSearchParams(window.location.search);

  if (params.get('open-all')) {
    for (const tab of document.getElementsByClassName('tab-content')) {
      tab.removeAttribute('style');
    }

    return;
  }

  /* Resume the tab selection state from the window hash on page load.
   * substring to remove the # to match values in allTabs array.
   */
  if (allTabs.includes(window.location.hash.substring(1))) {
    document.querySelector(`a[href="${window.location.hash}"]`).click();
  }
})();
