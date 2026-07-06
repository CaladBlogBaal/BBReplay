import replayLoader from './infinite_scroll.js?v=1.0.2';

const replayManager = {
    previousValues: { p1: null, p2: null },
    replayString: new URLSearchParams(window.location.search),

    handleAnchorClick(event, icon, player, dropdownId) {
        event.preventDefault();
        this.replayString.set(`${player}_character_id`, icon.id);
        this.replayString.set('page', '1');
        this.loadNewReplays();
        const dropdown = document.getElementById(dropdownId);
        dropdown.style.background = `url(${icon.path}) no-repeat center center`;
        dropdown.style.backgroundSize = 'cover';
    },

    handleFieldInputs(fieldInput, parameter) {
        const currentValue = fieldInput.value.trim().toLowerCase();

        if (this.previousValues[parameter] === currentValue) {
            return;
        }

        if (currentValue === '') {
            this.replayString.delete(parameter);
        } else {
            this.replayString.set(parameter, currentValue);
        }
        this.replayString.set('page', '1');
        this.previousValues[parameter] = currentValue;
        this.loadNewReplays();
    },

    setupSearchFields() {
        if (window.location.href.includes('upload')) return;
        for (const key of ['p1', 'p2']) {
            const value = this.replayString.get(key);

            if (value) {
                const normalized = value.toLowerCase();
                this.replayString.set(key, normalized);
                this.replayString.set(key, normalized);
                this.previousValues[key] = normalized;
            }
        }

        const playerInput = document.getElementById('playerInput');
        const playerInput2 = document.getElementById('playerInput2');
        const dateInput = $('#dateField');
        // jquery uses "this" which could refer to the DOM
        const self = this;

        dateInput.daterangepicker({
            autoUpdateInput: true,
            locale: { cancelLabel: 'Clear', format: 'MMMM D, YYYY' },
        });

        dateInput.on('apply.daterangepicker', function(_event, picker) {
            const startDate = picker.startDate.format('MMMM D, YYYY');
            const endDate = picker.endDate.format('MMMM D, YYYY');
            const dateRange = JSON.stringify([
                picker.startDate.format('DD/MM/YYYY'),
                picker.endDate.format('DD/MM/YYYY'),
            ]);
            if (self.previousValues.datetime_ !== dateRange) {
                self.replayString.set('datetime_', dateRange);
                self.replayString.set('page', '1');
                self.previousValues.datetime_ = dateRange;
                self.loadNewReplays();
                $(this).val(`${startDate} - ${endDate}`);
            }
        });

        dateInput.on('cancel.daterangepicker', function() {
            self.replayString.delete('datetime_');
            self.replayString.set('page', '1');
            self.previousValues.datetime_ = null;
            self.loadNewReplays();
            $(this).val('');
        });

        const date = new Date();
        const currentDate = date.toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric',
        });
        dateInput.attr('placeholder', `November 5, 2017 - ${currentDate}`);

        playerInput.addEventListener('keydown', event => {
            if (event.key === 'Enter') this.handleFieldInputs(playerInput, 'p1');
        });
        playerInput.addEventListener('input', () => {
            if (playerInput.value.trim() === '') this.handleFieldInputs(playerInput, 'p1');
        });
        playerInput2.addEventListener('keydown', event => {
            if (event.key === 'Enter') this.handleFieldInputs(playerInput2, 'p2');
        });
        playerInput2.addEventListener('input', () => {
            if (playerInput2.value.trim() === '') this.handleFieldInputs(playerInput2, 'p2');
        });
    },

    loadNewReplays() {
        const query = new URLSearchParams(this.replayString.toString());
        query.set('page', '1');
        this.replayString = new URLSearchParams(query.toString());
        // history only records searches that actually became the active displayed result
        return replayLoader.startSearch(query).then(result => {
            if (!result?.accepted) return result;
            window.history.pushState(
                result.historyState,
                '',
                `?${query.toString()}`,
            );
            return result;
        });
    },

    fetchCharacterIcons() {
        fetch('/api/character-icons')
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => this.displaysSearch(data))
            .catch(error => console.error('Error fetching character icons:', error));
    },

    displaysSearch(characterIcons) {
        if (window.location.href.includes('upload')) return;
        const dropdownMenu = document.querySelector('#characterContainer');
        const dropdownMenu2 = document.querySelector('#characterContainer2');
        // defensive guard
        dropdownMenu.replaceChildren();
        dropdownMenu2.replaceChildren();
        // jquery uses "this" which could refer to the DOM
        const self = this;

        const createDefaultListItem = (menu, type) => {
            const liElement = document.createElement('li');
            liElement.classList.add('dropdown-item');
            const anchorElement = document.createElement('a');
            anchorElement.text = 'Any';
            anchorElement.setAttribute('data-id', '');
            anchorElement.addEventListener('click', function(event) {
                event.preventDefault();
                self.replayString.delete(`${type}_character_id`);
                self.replayString.set('page', '1');
                self.loadNewReplays();
                document.getElementById(menu).style.background = '';
            });
            liElement.appendChild(anchorElement);
            return liElement;
        };

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
            anchorElement.addEventListener('click', event => {
                self.handleAnchorClick(event, icon, 'p1', 'characterDropdown');
            });
            anchorElement2.addEventListener('click', event => {
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

    init() {
        this.fetchCharacterIcons();
        this.setupSearchFields();
    },
};

export default replayManager;