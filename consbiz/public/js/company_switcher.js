frappe.provide('frappe.ui');

frappe.ui.CompanySwitcher = class CompanySwitcher {
    constructor() {
        this.current_company = frappe.defaults.get_user_default("company") || "เลือกบริษัท";
        this.companies = [];
        this.setup();
    }

    setup() {
        const observer = new MutationObserver((mutations) => {
            if ($('#sidebar-company-switcher').length) return;

            const footer = $('.body-sidebar-bottom');
            if (footer.length) {
                this.get_companies_and_render(footer);
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    get_companies_and_render(footer) {
        if ($('#sidebar-company-switcher').length) return;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Company",
                fields: ["name", "company_logo"] // เพิ่ม company_logo เข้ามา
            },
            callback: (r) => {
                if (r.message && !$('#sidebar-company-switcher').length) {
                    this.companies = r.message;
                    this.render_ui(footer);
                    this.setup_events();
                }
            }
        });
    }

    render_ui(footer) {
        // หาข้อมูลโลโก้ของบริษัทปัจจุบัน
        const current_co_data = this.companies.find(c => c.name === this.current_company);
        const current_logo = current_co_data ? current_co_data.company_logo : null;

        const company_items = this.companies
            .map((co) => {
                // ส่วนแสดงผลโลโก้ในรายการ Dropdown
                const item_logo_html = co.company_logo
                    ? `<img src="${co.company_logo}" style="width: 20px; height: 20px; object-fit: contain; margin-right: 8px; border-radius: 4px;">`
                    : `<div class="mr-2 d-inline-flex align-center justify-center" style="width: 20px; height: 20px; background: var(--bg-light-gray); border-radius: 4px; font-size: 10px;">🏢</div>`;

                return `
                <li>
                    <button class="btn-reset dropdown-item d-flex align-items-center" data-company="${co.name}">
                        ${item_logo_html}
                        <span class="text-truncate">${co.name}</span>
                    </button>
                </li>`;
            })
            .join('');

        // ส่วนแสดงผลโลโก้บนปุ่มหลัก
        const main_logo_html = current_logo
            ? `<img src="${current_logo}" style="width: 100%; height: 100%; object-fit: contain; padding: 2px;">`
            : `<div class="avatar-frame standard-image" style="background-color: var(--blue-avatar-bg); color: var(--blue-avatar-color)">🏢</div>`;

        const html = `
            <div id="sidebar-company-switcher" class="nav-item dropup dropdown-navbar-user dropdown-mobile mt-2">
                <style>
                    #sidebar-company-switcher .btn-company-switcher {
                        width: 100%;
                        height: 40px;
                        text-decoration: none;
                        margin-bottom: -10px !important;
                    }
                    #sidebar-company-switcher .dropdown-menu {
                        margin-bottom: 0px;
                        width: 240px;
                        border-radius: 8px;
                        overflow-y: auto;
                        max-height: 300px;
                    }
                    #sidebar-company-switcher .avatar-frame {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        overflow: hidden;
                        background: white; /* พื้นหลังขาวเพื่อให้โลโก้เด่น */
                        width: 28px !important;
                        height: 28px !important;
                    }
                    body.sidebar-collapsed #sidebar-company-switcher .avatar-name-email {
                        display: none !important;
                    }
                    body.sidebar-collapsed #sidebar-company-switcher .btn-company-switcher {
                        justify-content: center !important;
                    }
                </style>
                
                <button class="align-center btn-reset flex nav-link btn-company-switcher" data-toggle="dropdown" aria-label="Company Menu" aria-expanded="false">
                    <div class="avatar avatar-medium" title="${this.current_company}">
                        <div class="avatar-frame standard-image">
                            ${main_logo_html}
                        </div>
                    </div>
                    <div class="avatar-name-email ml-2 text-small overflow-hidden w-75 text-left">
                        <span class="d-block text-truncate font-weight-bold" style="color: var(--text-color);">
                            ${this.current_company}
                        </span>
                        <span class="d-block text-secondary text-truncate">
                            เปลี่ยนบริษัท <i class="fa fa-caret-up ml-1" style="font-size: 8px;"></i>
                        </span>
                    </div>
                </button>
                <div class="dropdown-menu dropdown-menu-left shadow-lg" role="menu">
                    ${company_items}
                </div>
            </div>`;

        const user_section = footer.find('.dropdown-navbar-user');
        if (user_section.length) {
            user_section.before(html);
        } else {
            footer.append(html);
        }
    }

    setup_events() {
        $('body').off('click', '#sidebar-company-switcher .dropdown-item').on('click', '#sidebar-company-switcher .dropdown-item', (e) => {
            e.preventDefault();
            const company_name = $(e.currentTarget).data('company');

            frappe.call({
                method: 'consbiz.api.set_user_default_company',
                args: { company: company_name },
                callback: (r) => { if (r.message) window.location.reload(); }
            });
        });
    }
};

$(document).ready(() => { new frappe.ui.CompanySwitcher(); });