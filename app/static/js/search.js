import replayLoader from './infinite_scroll.js';

const replayManager = {
    // constant
    replayContainer: document.getElementById('replaysContainer'),
    // to track the state of input fields
    previousValues: {
        p1: null,
        p2: null,
    },
    // Initialize URLSearchParams outside to maintain query inputs
    replayString: new URLSearchParams(window.location.search),

    handleAnchorClick: function(event, icon, player, dropdownId) {
        event.preventDefault(); // Prevent the default link behavior
        const characterId = icon.id;
        this.replayString.set(`${player}_character_id`, characterId);
        this.replayString.set('page', '1');

        this.loadNewReplays();

        const dropdown = document.getElementById(dropdownId);
        dropdown.style.background = `url(${icon.path}) no-repeat center center`;
        dropdown.style.backgroundSize = 'cover';
    },

    handleFieldInputs: function(fieldInput, parameter) {
        const currentValue = fieldInput;
        if (currentValue !== this.previousValues[parameter]) {
            if (currentValue) {
                this.replayString.set(parameter, currentValue);
                this.loadNewReplays();
            } else {
                this.replayString.delete(parameter);
            }
            this.previousValues[parameter] = currentValue;
        }
    },

    setupFieldEvent: function(event, fieldInput, parameter) {
        if (event.key === 'Enter' || event.keyCode === 13) {
            this.handleFieldInputs(fieldInput.value, parameter);
        } else if (event.key === 'Back' || event.keyCode === 8) {
            let currentValue = fieldInput.value;
            if (!currentValue) {
                if (fieldInput.value !== this.previousValues[parameter]) {
                    // check if it's player inputs
                    if (parameter.startsWith('p')) {
                        this.replayString.delete(parameter);
                        this.loadNewReplays();
                    }
                    this.previousValues[parameter] = currentValue;
                }
        }
        }
    },

    setupSearchFields: function() {
        if (window.location.href.includes('upload')) return;
        const playerInput = document.getElementById('playerInput');
        const playerInput2 = document.getElementById('playerInput2');
        const dateInput = $('#dateField');
        const self = this; // To preserve the context of 'this'

        dateInput.daterangepicker({
            autoUpdateInput: true,
            locale: {
                cancelLabel: 'Clear',
                format: 'MMMM D, YYYY'
            }
        });

        dateInput.on('apply.daterangepicker', function(ev, picker) {

            const startDate = picker.startDate.format('MMMM D, YYYY');
            const endDate = picker.endDate.format('MMMM D, YYYY');
            let dateRange = JSON.stringify([picker.startDate.format('DD/MM/YYYY'),
                                                  picker.endDate.format('DD/MM/YYYY')]);
            if (self.previousValues['recorded_at'] !== dateRange) {
                self.replayString.set('recorded_at', dateRange);
                self.previousValues.recorded_at = dateRange
                self.loadNewReplays();
                $(this).val(startDate + ' - ' + endDate);
            }
        });

        dateInput.on('cancel.daterangepicker', function() {
            self.replayString.delete('recorded_at');
            self.previousValues.recorded_at = null;
            self.loadNewReplays();
            $(this).val('');
        });

        const date = new Date();
        let options = { year: 'numeric', month: 'long', day: 'numeric' };
        let currentDate = date.toLocaleDateString("en-US", options);
        // MMMM D, YYYY
        dateInput.attr('placeholder', 'November 5, 2017' + ' - ' + currentDate);

        playerInput.addEventListener('keyup', function(event) {
            self.setupFieldEvent(event, playerInput, 'p1');
        });

        playerInput2.addEventListener('keyup', function(event) {
            self.setupFieldEvent(event, playerInput2, 'p2');
        });

        playerInput.addEventListener('blur', function() {
            self.handleFieldInputs(playerInput.value, 'p1');
        });

        playerInput2.addEventListener('blur', function() {
            self.handleFieldInputs(playerInput2.value, 'p2');
        });

    },

    loadNewReplays: function() {
        this.replayContainer.replaceChildren();
        replayLoader.loadReplays(this.replayString).then(
            r => window.history.pushState(r, '', '?' + this.replayString.toString()))
    },

    fetchCharacterIcons: function() {
        fetch('/api/character-icons')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                this.displaysSearch(data);
            })
            .catch(error => {
                console.error('Error fetching character icons:', error);
            });
    },

    displaysSearch: function(characterIcons) {
        if (window.location.href.includes('upload')) return;
        const dropdownMenu = document.querySelector('#characterContainer');
        const dropdownMenu2 = document.querySelector('#characterContainer2');
        const self = this; // To preserve the context of 'this'

        // Create a default reset list item
        const createDefaultListItem = (menu, type) => {
            const liElement = document.createElement('li');
            liElement.classList.add('dropdown-item');
            const anchorElement = document.createElement('a');
            anchorElement.text = 'Any'; // Text for the default option
            anchorElement.setAttribute('data-id', ''); // Blank data-id to indicate reset

            anchorElement.addEventListener('click', function(event) {
                event.preventDefault(); // Prevent the default link behavior
                self.replayString.delete(`${type}_character_id`);
                self.replayString.set('page', '1');
                self.loadNewReplays(); //  reload to list
                const dropdown = document.getElementById(menu);
                dropdown.style.background = ''
            });

        liElement.appendChild(anchorElement);
        return liElement;
        };

        // Append default list item to both dropdown menus
        dropdownMenu.appendChild(createDefaultListItem('characterDropdown', 'p1'));
        dropdownMenu2.appendChild(createDefaultListItem('characterDropdown2', 'p2'));

        characterIcons.forEach(icon => {
            const liElement = document.createElement('li');
            liElement.classList.add('dropdown-item');
            const imgElement = document.createElement('img');
            imgElement.src = icon.path;
            const anchorElement = document.createElement('a');
            anchorElement.text = icon.name;
            anchorElement.setAttribute('data-id', icon.id);

            const anchorElement2 = anchorElement.cloneNode(true);
            const imgElement2 = imgElement.cloneNode(true);
            const liElement2 = liElement.cloneNode(true);

            anchorElement.addEventListener('click', function(event) {
                self.handleAnchorClick(event, icon, 'p1', 'characterDropdown');
            });

            anchorElement2.addEventListener('click', function(event) {
                self.handleAnchorClick(event, icon, 'p2', 'characterDropdown2');
            });

            dropdownMenu.appendChild(liElement);
            dropdownMenu2.appendChild(liElement2);
            liElement.appendChild(anchorElement);
            liElement2.appendChild(anchorElement2);
            anchorElement.appendChild(imgElement);
            anchorElement2.appendChild(imgElement2);
        });
    },

    init: async function() {
        this.fetchCharacterIcons();
        this.setupSearchFields();
    }
};

export default replayManager;
