/* STN crisis panel: pure view model (no DOM). Tested in Node by tests/crisis-panel.test.js. */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.STNCrisisModel = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function buildModel(data, regionId) {
    if (!data || data.schema !== 'stn-crisis-resources/1') throw new Error('Unknown crisis register');
    var region = null;
    if (regionId) {
      region = data.regions.filter(function (r) { return r.id === regionId; })[0] || null;
    }
    var tiers = data.tiers.slice().sort(function (a, b) { return a.order - b.order; }).map(function (tier) {
      var items = [];
      tier.actions.forEach(function (action) {
        if (!action.regional) {
          items.push({ kind: 'contact', label: action.label, phone: action.phone || null, tel: action.tel || null,
            sms: action.sms || null, hours: action.hours, detail: action.detail });
          return;
        }
        if (!region) {
          items.push({ kind: 'choose_region', label: action.label, hours: action.hours, detail: action.detail });
        } else if (!region.teams.length) {
          items.push({ kind: 'see_source', label: action.label + ': ' + region.name, hours: action.hours,
            detail: data.see_source_text });
        } else {
          region.teams.forEach(function (team) {
            items.push({ kind: 'contact', label: 'Crisis team: ' + team.place, phone: team.phone, tel: team.tel,
              sms: null, hours: action.hours, detail: region.status === 'checked' ? '' :
                'Number transcribed from the Mental Health Foundation directory (June 2026); check before relying on it.' });
          });
        }
      });
      return { id: tier.id, heading: tier.heading, when: tier.when, items: items };
    });
    return {
      provisional: !(data.approval && data.approval.clinically_approved === true),
      notice: data.approval ? data.approval.notice : '',
      statement: data.stn_statement,
      verifiedOn: data.verified_on,
      regions: data.regions.map(function (r) { return { id: r.id, name: r.name }; }),
      selectedRegion: region ? region.id : null,
      tiers: tiers,
      sources: data.sources
    };
  }

  return { buildModel: buildModel };
}));
