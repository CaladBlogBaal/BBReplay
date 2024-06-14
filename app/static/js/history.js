import replayLoader from "./infinite_scroll.js";
import replayManager from "./search.js";

function waitForElm(selector) {
    return new Promise(resolve => {
        if (document.querySelector(selector)) {
            return resolve(document.querySelector(selector));
        }

        const observer = new MutationObserver(mutations => {
            if (document.querySelector(selector)) {
                observer.disconnect();
                resolve(document.querySelector(selector));
            }
        });

        // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}

function populateFieldsWithParameters() {
    if (window.location.href.includes('upload')) return;
    const searchParams = new URLSearchParams(window.location.search);
    const dateInput = $('#dateField');
    const playerInput = document.getElementById('playerInput');
    const playerInput2 = document.getElementById('playerInput2');

    function handleCharacterIcon(fieldValue, dropdownID, characterContainerID) {

        const characterDropdown = document.getElementById(dropdownID);
        const characterContainer = document.getElementById(characterContainerID);

        const collection = characterContainer.getElementsByClassName('dropdown-item');

        Array.prototype.forEach.call(collection, function(item) {
            const aTag = item.getElementsByTagName('a')[0];
            const dataID = aTag.getAttribute('data-id');
            if (dataID === fieldValue) {
                if (fieldValue !== '') {
                    const imgPath = aTag.getElementsByTagName('img')[0].getAttribute('src');
                    characterDropdown.style.background = `url(${imgPath}) no-repeat center center`;
                    characterDropdown.style.backgroundSize = 'cover';
                } else {
                    characterDropdown.style.background = '';
                }
            }
        });
    }
    for (const [key, value] of searchParams.entries()) {
        if (key === 'recorded_at') {
          const dates = JSON.parse(value);
          dateInput.attr('placeholder', dates.join(' - '));
        } else if (key === 'p1') {
            playerInput.value = value;
        } else if (key === 'p2') {
            playerInput2.value = value;
        } // else if (key === 'p1_character_id') {
          //  handleCharacterIcon(value,'characterDropdown', 'characterContainer');
        //} else if (key === 'p2_character_id') {
        //    handleCharacterIcon(value, 'characterDropdown2', 'characterContainer2');
       // }
    }
    const value = searchParams.get('p1_character_id') || '';
    const value2 = searchParams.get('p2_character_id') || '';
    handleCharacterIcon(value,'characterDropdown', 'characterContainer');
    handleCharacterIcon(value2, 'characterDropdown2', 'characterContainer2');
}

// https://developer.mozilla.org/en-US/docs/Web/API/History_API/Working_with_the_History_API#using_pushstate
window.addEventListener("popstate", (event) => {
    if (event.state) {
        const replayContainer = document.getElementById('replays-container')
        replayContainer.replaceChildren();
        replayLoader.maxPage = event.state.maxPage;
        replayLoader.replayString = new URLSearchParams(window.location.search);
        // Convert page to a number before adding 1
        replayLoader.page = Number(replayLoader.replayString.get('page')) + 1 || 1;
        event.state.replays.forEach(replay => {
          $('#replays-container').append(replayLoader.renderReplay(replay));
        });
        replayLoader.replayString.set('page', replayLoader.page.toString());

      $(document).ready(function () {
          populateFieldsWithParameters();
      })
  }
});

$(document).ready(function() {
    replayManager.init().then(
        populateFieldsWithParameters()
    );
    replayLoader.loadReplays(new URLSearchParams(window.location.search)).then(
        r => history.replaceState(r, '', window.location.search)
    );
});
