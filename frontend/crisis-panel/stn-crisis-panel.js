/* <stn-crisis-panel> custom element. No inline scripts or handlers; works under script-src 'self'.
 * Data: window.STN_CRISIS_RESOURCES (crisis-resources.js, generated from backend/app/data/crisis_resources.json).
 * Attributes: region (optional region id, remembered for this browser only).
 */
(function () {
  'use strict';
  var STORAGE_KEY = 'stn.crisisPanel.region';

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text) node.textContent = text;
    return node;
  }

  function rememberedRegion() {
    try { return window.localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }  // region only, never personal data
  }

  function remember(regionId) {
    try { window.localStorage.setItem(STORAGE_KEY, regionId || ''); } catch (e) { /* storage unavailable: fine */ }
  }

  class STNCrisisPanel extends HTMLElement {
    connectedCallback() {
      this.render(this.getAttribute('region') || rememberedRegion() || null);
    }

    render(regionId) {
      var model = window.STNCrisisModel.buildModel(window.STN_CRISIS_RESOURCES, regionId);
      var root = el('section', { class: 'stn-crisis', 'aria-labelledby': 'stn-crisis-title' });
      root.appendChild(el('h2', { id: 'stn-crisis-title' }, 'Need help now?'));
      root.appendChild(el('p', { class: 'stn-crisis-statement' }, model.statement));
      if (model.provisional) {
        root.appendChild(el('p', { class: 'stn-crisis-provisional', role: 'note' }, model.notice));
      }

      var label = el('label', { for: 'stn-crisis-region' }, 'Your region (for your local crisis team)');
      var select = el('select', { id: 'stn-crisis-region' });
      select.appendChild(el('option', { value: '' }, 'Choose your region'));
      model.regions.forEach(function (r) {
        var opt = el('option', { value: r.id }, r.name);
        if (r.id === model.selectedRegion) opt.selected = true;
        select.appendChild(opt);
      });
      var self = this;
      select.addEventListener('change', function () {
        remember(select.value);
        self.render(select.value || null);
        var again = self.querySelector('#stn-crisis-region');
        if (again) again.focus();
      });
      var picker = el('div', { class: 'stn-crisis-region' });
      picker.appendChild(label);
      picker.appendChild(select);
      root.appendChild(picker);

      var live = el('div', { 'aria-live': 'polite' });
      model.tiers.forEach(function (tier) {
        var box = el('div', { class: 'stn-crisis-tier stn-crisis-' + tier.id, 'data-tier': tier.id });
        box.appendChild(el('h3', {}, tier.heading));
        box.appendChild(el('p', { class: 'stn-crisis-when' }, tier.when));
        var list = el('ul', {});
        tier.items.forEach(function (item) {
          var li = el('li', { 'data-kind': item.kind });
          li.appendChild(el('span', { class: 'stn-crisis-label' }, item.label));
          if (item.tel) {
            li.appendChild(el('a', { class: 'stn-crisis-call', href: 'tel:' + item.tel }, 'Call ' + item.phone));
          }
          if (item.sms) {
            li.appendChild(el('a', { class: 'stn-crisis-call', href: 'sms:' + item.sms }, 'Text ' + item.sms));
          }
          li.appendChild(el('span', { class: 'stn-crisis-hours' }, 'Hours: ' + item.hours));
          if (item.detail) li.appendChild(el('span', { class: 'stn-crisis-detail' }, item.detail));
          list.appendChild(li);
        });
        box.appendChild(list);
        live.appendChild(box);
      });
      root.appendChild(live);
      root.appendChild(el('p', { class: 'stn-crisis-verified' }, 'Contact details checked ' + model.verifiedOn + '.'));
      this.replaceChildren(root);
    }
  }

  if (!customElements.get('stn-crisis-panel')) customElements.define('stn-crisis-panel', STNCrisisPanel);
}());
