import {
  LitElement,
  html,
  css,
  unsafeCSS,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

// Inlined shared styles for HA panel compatibility
const sharedStylesLit = `
  /* TOP BAR - matches HA standard header */
  .top-bar {
    display: flex;
    align-items: center;
    height: 56px;
    padding: 0 16px;
    background: var(--app-header-background-color, var(--primary-background-color));
    color: var(--app-header-text-color, var(--primary-text-color));
    position: sticky;
    top: 0;
    z-index: 100;
    gap: 12px;
    margin: -16px -16px 16px -16px;
    border-bottom: 1px solid var(--divider-color);
  }
  .top-bar-sidebar-btn {
    width: 40px;
    height: 40px;
    border: none;
    background: transparent;
    color: var(--app-header-text-color, var(--primary-text-color));
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background 0.2s;
    flex-shrink: 0;
  }
  .top-bar-sidebar-btn:hover { background: rgba(127, 127, 127, 0.2); }
  .top-bar-sidebar-btn svg { width: 24px; height: 24px; }
  .top-bar-title {
    flex: 1;
    font-size: 20px;
    font-weight: 500;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .top-bar-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
  .top-bar-action-btn {
    width: 40px;
    height: 40px;
    border: none;
    background: transparent;
    color: var(--app-header-text-color, var(--primary-text-color));
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background 0.2s;
  }
  .top-bar-action-btn:hover { background: rgba(127, 127, 127, 0.2); }
  .top-bar-action-btn svg { width: 24px; height: 24px; }

  /* SEARCH ROW */
  .search-row {
    display: flex;
    align-items: center;
    height: 48px;
    padding: 0 16px;
    background: var(--primary-background-color);
    border-bottom: 1px solid var(--divider-color);
    margin: 0 -16px 16px -16px;
    gap: 8px;
  }
  .search-row-input-wrapper {
    flex: 1;
    display: flex;
    align-items: center;
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 0 12px;
    height: 36px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .search-row-input-wrapper:focus-within {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 2px rgba(var(--rgb-primary-color, 3, 169, 244), 0.2);
  }
  .search-row-icon {
    width: 20px;
    height: 20px;
    color: var(--secondary-text-color);
    flex-shrink: 0;
    margin-right: 8px;
  }
  .search-row-input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 14px;
    color: var(--primary-text-color);
    outline: none;
    height: 100%;
  }
  .search-row-input::placeholder { color: var(--secondary-text-color); }
`;

// Translation helper
const commonTranslations = {
  en: { menu: 'Menu', search: 'Search...', add: 'Add', more_actions: 'More actions' },
  'zh-Hant': { menu: '選單', search: '搜尋...', add: '新增', more_actions: '更多操作' },
  'zh-Hans': { menu: '菜单', search: '搜索...', add: '添加', more_actions: '更多操作' },
};
function getCommonTranslation(key, lang = 'en') {
  const langKey = lang?.startsWith('zh-TW') || lang?.startsWith('zh-HK') ? 'zh-Hant' :
                  lang?.startsWith('zh') ? 'zh-Hans' : 'en';
  return commonTranslations[langKey]?.[key] || commonTranslations['en'][key] || key;
}

class HaAssetPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      panel: { type: Object },
      _assets: { type: Array },
      _loading: { type: Boolean },
      _dialogOpen: { type: Boolean },
      _editingAsset: { type: Object },
      _deleteConfirmOpen: { type: Boolean },
      _saving: { type: Boolean },
      _nameError: { type: Boolean },
      _searchQuery: { type: String },
    };
  }

  static get styles() {
    return css`
      ${unsafeCSS(sharedStylesLit)}

      :host {
        display: block;
        height: 100%;
        background: var(--primary-background-color);
      }

      .container {
        padding: 16px;
        max-width: 1200px;
        margin: 0 auto;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }

      .header h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 400;
        color: var(--primary-text-color);
      }

      .add-button {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .add-button:hover {
        opacity: 0.9;
      }

      .table-container {
        background: var(--card-background-color);
        border-radius: 8px;
        overflow-x: auto;
        box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0,0,0,0.1));
        -webkit-overflow-scrolling: touch;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        min-width: 600px;
      }

      th, td {
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid var(--divider-color);
        white-space: nowrap;
      }

      /* Name column can wrap */
      th:first-child, td:first-child {
        white-space: normal;
        min-width: 120px;
        max-width: 200px;
      }

      th {
        background: var(--table-header-background-color, var(--secondary-background-color));
        font-weight: 500;
        color: var(--primary-text-color);
        position: sticky;
        top: 0;
      }

      tr:hover {
        background: var(--table-row-background-color, rgba(0,0,0,0.04));
        cursor: pointer;
      }

      tr:last-child td {
        border-bottom: none;
      }

      /* Mobile responsive - card layout */
      @media (max-width: 600px) {
        table {
          min-width: unset;
        }

        thead {
          display: none;
        }

        tbody tr {
          display: block;
          padding: 12px 16px;
          border-bottom: 1px solid var(--divider-color);
        }

        tbody tr:last-child {
          border-bottom: none;
        }

        tbody td {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 4px 0;
          border-bottom: none;
          white-space: normal;
        }

        tbody td::before {
          content: attr(data-label);
          font-weight: 500;
          color: var(--secondary-text-color);
          font-size: 12px;
          min-width: 80px;
          margin-right: 8px;
        }

        /* Name row styling */
        tbody td:first-child {
          font-weight: 500;
          font-size: 16px;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--divider-color);
          margin-bottom: 8px;
        }

        tbody td:first-child::before {
          display: none;
        }
      }

      .warranty-ok {
        color: var(--success-color, #4caf50);
      }

      .warranty-warning {
        color: var(--warning-color, #ff9800);
      }

      .warranty-expired {
        color: var(--error-color, #f44336);
      }

      .summary {
        margin-top: 16px;
        padding: 16px;
        background: var(--card-background-color);
        border-radius: 8px;
        display: flex;
        gap: 32px;
        box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0,0,0,0.1));
      }

      .summary-item {
        display: flex;
        flex-direction: column;
      }

      .summary-label {
        font-size: 12px;
        color: var(--secondary-text-color);
      }

      .summary-value {
        font-size: 20px;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      .empty-state {
        text-align: center;
        padding: 48px 16px;
        color: var(--secondary-text-color);
      }

      .empty-state ha-icon {
        --mdc-icon-size: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
      }

      /* Dialog styles */
      .dialog-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .dialog {
        background: var(--card-background-color);
        border-radius: 8px;
        width: 90%;
        max-width: 500px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      }

      .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid var(--divider-color);
      }

      .dialog-header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 500;
      }

      .dialog-close {
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px;
        color: var(--secondary-text-color);
      }

      .dialog-content {
        padding: 16px;
      }

      .form-group {
        margin-bottom: 16px;
      }

      .form-group label {
        display: block;
        margin-bottom: 4px;
        font-size: 14px;
        color: var(--primary-text-color);
      }

      .form-group input,
      .form-group textarea {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        font-size: 14px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        box-sizing: border-box;
      }

      .form-group textarea {
        min-height: 80px;
        resize: vertical;
      }

      .form-group input:focus,
      .form-group textarea:focus {
        outline: none;
        border-color: var(--primary-color);
      }

      .dialog-footer {
        display: flex;
        justify-content: space-between;
        padding: 16px;
        border-top: 1px solid var(--divider-color);
      }

      .dialog-footer-left {
        display: flex;
      }

      .dialog-footer-right {
        display: flex;
        gap: 8px;
      }

      .btn {
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
        cursor: pointer;
        border: none;
      }

      .btn-primary {
        background: var(--primary-color);
        color: var(--text-primary-color);
      }

      .btn-secondary {
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }

      .btn-danger {
        background: var(--error-color, #f44336);
        color: white;
      }

      .btn:hover {
        opacity: 0.9;
      }

      .loading {
        display: flex;
        justify-content: center;
        padding: 48px;
      }

      .form-group.error input {
        border-color: var(--error-color, #f44336);
      }

      .form-group .error-message {
        color: var(--error-color, #f44336);
        font-size: 12px;
        margin-top: 4px;
      }

      .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    `;
  }

  constructor() {
    super();
    this._assets = [];
    this._loading = true;
    this._dialogOpen = false;
    this._editingAsset = null;
    this._deleteConfirmOpen = false;
    this._saving = false;
    this._nameError = false;
    this._searchQuery = "";
    this._boundHandleKeydown = this._handleKeydown.bind(this);
  }

  _toggleSidebar() {
    this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  _onSearchInput(e) {
    this._searchQuery = e.target.value;
  }

  _getFilteredAssets() {
    if (!this._searchQuery || !this._searchQuery.trim()) {
      return this._assets;
    }
    const query = this._searchQuery.toLowerCase().trim();
    return this._assets.filter((asset) => {
      const name = (asset.name || "").toLowerCase();
      const brand = (asset.brand || "").toLowerCase();
      const category = (asset.category || "").toLowerCase();
      return name.includes(query) || brand.includes(query) || category.includes(query);
    });
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadAssets();
    document.addEventListener("keydown", this._boundHandleKeydown);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener("keydown", this._boundHandleKeydown);
  }

  _handleKeydown(e) {
    if (e.key === "Escape" && this._dialogOpen) {
      this._closeDialog();
    }
  }

  async _loadAssets() {
    this._loading = true;
    try {
      const result = await this.hass.callWS({ type: "ha_asset_record/list" });
      this._assets = result.assets || [];
    } catch (e) {
      console.error("Failed to load assets:", e);
      this._assets = [];
    }
    this._loading = false;
  }

  _localize(key) {
    // Try to get translation from HA
    const translation = this.hass?.localize?.(`component.ha_asset_record.panel.${key}`);
    if (translation) return translation;

    // Fallback translations
    const fallbacks = {
      title: this.hass?.language === "zh-Hant" ? "資產管理" : "Asset Dashboard",
      add_asset: this.hass?.language === "zh-Hant" ? "新增設備" : "Add Asset",
      edit_asset: this.hass?.language === "zh-Hant" ? "編輯設備" : "Edit Asset",
      name: this.hass?.language === "zh-Hant" ? "名稱" : "Name",
      brand: this.hass?.language === "zh-Hant" ? "品牌" : "Brand",
      category: this.hass?.language === "zh-Hant" ? "類型" : "Category",
      value: this.hass?.language === "zh-Hant" ? "價值" : "Value",
      warranty: this.hass?.language === "zh-Hant" ? "保固" : "Warranty",
      purchase_at: this.hass?.language === "zh-Hant" ? "購買時間" : "Purchase Date",
      warranty_until: this.hass?.language === "zh-Hant" ? "保固到期" : "Warranty Until",
      manual: this.hass?.language === "zh-Hant" ? "使用說明" : "Manual",
      maintenance: this.hass?.language === "zh-Hant" ? "維修說明" : "Maintenance",
      save: this.hass?.language === "zh-Hant" ? "儲存" : "Save",
      cancel: this.hass?.language === "zh-Hant" ? "取消" : "Cancel",
      delete: this.hass?.language === "zh-Hant" ? "刪除" : "Delete",
      delete_confirm: this.hass?.language === "zh-Hant" ? "確定要刪除此設備嗎？" : "Are you sure you want to delete this asset?",
      total_assets: this.hass?.language === "zh-Hant" ? "設備總數" : "Total Assets",
      total_value: this.hass?.language === "zh-Hant" ? "總價值" : "Total Value",
      no_assets: this.hass?.language === "zh-Hant" ? "尚無設備資料" : "No assets yet",
      no_assets_hint: this.hass?.language === "zh-Hant" ? "點擊上方按鈕新增您的第一個設備" : "Click the button above to add your first asset",
      expired: this.hass?.language === "zh-Hant" ? "已過期" : "Expired",
      name_required: this.hass?.language === "zh-Hant" ? "名稱為必填" : "Name is required",
    };
    return fallbacks[key] || key;
  }

  _formatDate(dateStr) {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString(this.hass?.language || "en");
  }

  _formatValue(value) {
    if (value === null || value === undefined || value === 0) return "-";
    return value.toLocaleString(this.hass?.language || "en");
  }

  _getWarrantyStatus(warrantyUntil) {
    if (!warrantyUntil) return { class: "", text: "-" };

    const now = new Date();
    const warranty = new Date(warrantyUntil);
    const daysLeft = Math.ceil((warranty - now) / (1000 * 60 * 60 * 24));

    if (daysLeft < 0) {
      return { class: "warranty-expired", text: `⚠️ ${this._localize("expired")}` };
    } else if (daysLeft <= 30) {
      return { class: "warranty-warning", text: this._formatDate(warrantyUntil) };
    }
    return { class: "warranty-ok", text: this._formatDate(warrantyUntil) };
  }

  _openAddDialog() {
    this._editingAsset = {
      name: "",
      brand: "",
      category: "",
      value: 0,
      purchase_at: "",
      warranty_until: "",
      manual_md: "",
      maintenance_md: "",
    };
    this._dialogOpen = true;
  }

  _openEditDialog(asset) {
    this._editingAsset = { ...asset };
    this._dialogOpen = true;
  }

  _closeDialog() {
    this._dialogOpen = false;
    this._editingAsset = null;
    this._deleteConfirmOpen = false;
    this._nameError = false;
  }

  async _saveAsset() {
    // Validate name (trim whitespace)
    const name = (this._editingAsset?.name || "").trim();
    if (!name) {
      this._nameError = true;
      return;
    }
    this._nameError = false;

    // Prevent double submission
    if (this._saving) return;
    this._saving = true;

    try {
      if (this._editingAsset.id) {
        // Update existing
        await this.hass.callWS({
          type: "ha_asset_record/update",
          asset_id: this._editingAsset.id,
          name: this._editingAsset.name,
          brand: this._editingAsset.brand || "",
          category: this._editingAsset.category || "",
          value: parseFloat(this._editingAsset.value) || 0,
          purchase_at: this._editingAsset.purchase_at || null,
          warranty_until: this._editingAsset.warranty_until || null,
          manual_md: this._editingAsset.manual_md || "",
          maintenance_md: this._editingAsset.maintenance_md || "",
        });
      } else {
        // Create new
        await this.hass.callWS({
          type: "ha_asset_record/create",
          name: this._editingAsset.name,
          brand: this._editingAsset.brand || "",
          category: this._editingAsset.category || "",
          value: parseFloat(this._editingAsset.value) || 0,
          purchase_at: this._editingAsset.purchase_at || null,
          warranty_until: this._editingAsset.warranty_until || null,
          manual_md: this._editingAsset.manual_md || "",
          maintenance_md: this._editingAsset.maintenance_md || "",
        });
      }
      this._closeDialog();
      await this._loadAssets();
    } catch (e) {
      console.error("Failed to save asset:", e);
    } finally {
      this._saving = false;
    }
  }

  async _deleteAsset() {
    if (!this._editingAsset?.id) return;

    try {
      await this.hass.callWS({
        type: "ha_asset_record/delete",
        asset_id: this._editingAsset.id,
      });
      this._closeDialog();
      await this._loadAssets();
    } catch (e) {
      console.error("Failed to delete asset:", e);
    }
  }

  _handleInput(e, field) {
    this._editingAsset = {
      ...this._editingAsset,
      [field]: e.target.value,
    };
  }

  _renderTable() {
    const filteredAssets = this._getFilteredAssets();

    if (this._assets.length === 0) {
      return html`
        <div class="table-container">
          <div class="empty-state">
            <ha-icon icon="mdi:package-variant-closed"></ha-icon>
            <div>${this._localize("no_assets")}</div>
            <div style="font-size: 14px; margin-top: 8px;">${this._localize("no_assets_hint")}</div>
          </div>
        </div>
      `;
    }

    if (filteredAssets.length === 0) {
      return html`
        <div class="table-container">
          <div class="empty-state">
            <ha-icon icon="mdi:magnify"></ha-icon>
            <div>No assets match your search</div>
          </div>
        </div>
      `;
    }

    return html`
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>${this._localize("name")}</th>
              <th>${this._localize("brand")}</th>
              <th>${this._localize("category")}</th>
              <th>${this._localize("value")}</th>
              <th>${this._localize("warranty")}</th>
            </tr>
          </thead>
          <tbody>
            ${filteredAssets.map(asset => {
              const warranty = this._getWarrantyStatus(asset.warranty_until);
              return html`
                <tr @click=${() => this._openEditDialog(asset)}>
                  <td data-label="${this._localize("name")}">${asset.name}</td>
                  <td data-label="${this._localize("brand")}">${asset.brand || "-"}</td>
                  <td data-label="${this._localize("category")}">${asset.category || "-"}</td>
                  <td data-label="${this._localize("value")}">${this._formatValue(asset.value)}</td>
                  <td data-label="${this._localize("warranty")}" class=${warranty.class}>${warranty.text}</td>
                </tr>
              `;
            })}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderSummary() {
    const totalAssets = this._assets.length;
    const totalValue = this._assets.reduce((sum, a) => sum + (a.value || 0), 0);

    return html`
      <div class="summary">
        <div class="summary-item">
          <span class="summary-label">${this._localize("total_assets")}</span>
          <span class="summary-value">${totalAssets}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">${this._localize("total_value")}</span>
          <span class="summary-value">${this._formatValue(totalValue)}</span>
        </div>
      </div>
    `;
  }

  _renderDialog() {
    const isEditing = !!this._editingAsset?.id;
    const title = isEditing ? this._localize("edit_asset") : this._localize("add_asset");

    return html`
      <div class="dialog-backdrop" @click=${this._closeDialog}>
        <div class="dialog" @click=${e => e.stopPropagation()}>
          <div class="dialog-header">
            <h2>${title}</h2>
            <button class="dialog-close" @click=${this._closeDialog}>✕</button>
          </div>

          <div class="dialog-content">
            <div class="form-group ${this._nameError ? "error" : ""}">
              <label>${this._localize("name")} *</label>
              <input
                type="text"
                .value=${this._editingAsset?.name || ""}
                @input=${e => {
                  this._handleInput(e, "name");
                  this._nameError = false;
                }}
              />
              ${this._nameError ? html`<div class="error-message">${this._localize("name_required")}</div>` : ""}
            </div>

            <div class="form-group">
              <label>${this._localize("brand")}</label>
              <input
                type="text"
                .value=${this._editingAsset?.brand || ""}
                @input=${e => this._handleInput(e, "brand")}
              />
            </div>

            <div class="form-group">
              <label>${this._localize("category")}</label>
              <input
                type="text"
                .value=${this._editingAsset?.category || ""}
                @input=${e => this._handleInput(e, "category")}
              />
            </div>

            <div class="form-group">
              <label>${this._localize("value")}</label>
              <input
                type="number"
                .value=${this._editingAsset?.value || 0}
                @input=${e => this._handleInput(e, "value")}
              />
            </div>

            <div class="form-group">
              <label>${this._localize("purchase_at")}</label>
              <input
                type="date"
                .value=${this._editingAsset?.purchase_at?.split("T")[0] || ""}
                @input=${e => this._handleInput(e, "purchase_at")}
              />
            </div>

            <div class="form-group">
              <label>${this._localize("warranty_until")}</label>
              <input
                type="date"
                .value=${this._editingAsset?.warranty_until?.split("T")[0] || ""}
                @input=${e => this._handleInput(e, "warranty_until")}
              />
            </div>

            <div class="form-group">
              <label>${this._localize("manual")}</label>
              <textarea
                .value=${this._editingAsset?.manual_md || ""}
                @input=${e => this._handleInput(e, "manual_md")}
              ></textarea>
            </div>

            <div class="form-group">
              <label>${this._localize("maintenance")}</label>
              <textarea
                .value=${this._editingAsset?.maintenance_md || ""}
                @input=${e => this._handleInput(e, "maintenance_md")}
              ></textarea>
            </div>
          </div>

          ${this._deleteConfirmOpen
            ? html`
                <div class="dialog-footer" style="background: var(--error-color); color: white;">
                  <div>${this._localize("delete_confirm")}</div>
                  <div class="dialog-footer-right">
                    <button class="btn btn-secondary" @click=${() => (this._deleteConfirmOpen = false)}>
                      ${this._localize("cancel")}
                    </button>
                    <button class="btn btn-danger" @click=${this._deleteAsset}>
                      ${this._localize("delete")}
                    </button>
                  </div>
                </div>
              `
            : html`
                <div class="dialog-footer">
                  <div class="dialog-footer-left">
                    ${isEditing
                      ? html`
                          <button class="btn btn-danger" @click=${() => (this._deleteConfirmOpen = true)}>
                            ${this._localize("delete")}
                          </button>
                        `
                      : ""}
                  </div>
                  <div class="dialog-footer-right">
                    <button class="btn btn-secondary" @click=${this._closeDialog} ?disabled=${this._saving}>
                      ${this._localize("cancel")}
                    </button>
                    <button class="btn btn-primary" @click=${this._saveAsset} ?disabled=${this._saving}>
                      ${this._saving ? "..." : this._localize("save")}
                    </button>
                  </div>
                </div>
              `}
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="container">
        <!-- Top Bar -->
        <div class="top-bar">
          <button class="top-bar-sidebar-btn" @click=${this._toggleSidebar} title="${getCommonTranslation('menu', this.hass?.language)}">
            <svg viewBox="0 0 24 24"><path fill="currentColor" d="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"/></svg>
          </button>
          <h1 class="top-bar-title">${this._localize("title")}</h1>
          <div class="top-bar-actions">
            <button class="top-bar-action-btn" @click=${this._openAddDialog} title="${this._localize("add_asset")}">
              <svg viewBox="0 0 24 24"><path fill="currentColor" d="M17,13H13V17H11V13H7V11H11V7H13V11H17M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/></svg>
            </button>
          </div>
        </div>

        <!-- Search Row -->
        <div class="search-row">
          <div class="search-row-input-wrapper">
            <svg class="search-row-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/></svg>
            <input
              class="search-row-input"
              type="text"
              placeholder="${getCommonTranslation('search', this.hass?.language)}"
              .value=${this._searchQuery}
              @input=${this._onSearchInput}
            />
          </div>
        </div>

        ${this._loading
          ? html`<div class="loading"><ha-circular-progress active></ha-circular-progress></div>`
          : html`
              ${this._renderTable()}
              ${this._renderSummary()}
            `}

        ${this._dialogOpen ? this._renderDialog() : ""}
      </div>
    `;
  }
}

customElements.define("ha-asset-panel", HaAssetPanel);
