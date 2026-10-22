frappe.provide('frappe.ui');

// ปุ่มเปลี่ยนบริษัท มี 2 ที่ ใช้ avatar และเมนู (frappe.ui.Dropdown) ชุดเดียวกัน:
// - Dock (แถบซ้ายของ Frappe v16): ปุ่มกลมในกล่อง .dock-company เหนือ .dock-user (Avatar)
//   ห้ามใส่ไว้ใน .dock-user เพราะ Frappe ผูกคลิกทั้งกล่องนั้นกับเมนูผู้ใช้
// - Sidebar: แถวเหนือแถวผู้ใช้ หน้าตาเหมือนแถวผู้ใช้ของ Frappe
//   แสดง/ซ่อนพร้อมแถวผู้ใช้: ซ่อนตอน Dock แบบ Pinned, แสดงตอน Floating (ตั้งค่าผู้ใช้ > Dock)
frappe.ui.CompanySwitcher = class CompanySwitcher {
    constructor() {
        this.current_company = frappe.defaults.get_user_default("company") || "เลือกบริษัท";
        this.companies = null;
        this.setup();
    }

    setup() {
        const observer = new MutationObserver(() => {
            const dock = $('#desk-dock');
            if (dock.length && !dock.find('.dock-company').length) {
                this.load_companies().then(() => this.render_dock(dock));
            }

            const footer = $('.body-sidebar-bottom');
            if (footer.length && !$('#sidebar-company-switcher').length) {
                this.load_companies().then(() => this.render_sidebar(footer));
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    load_companies() {
        if (!this.companies_promise) {
            this.companies_promise = frappe
                .call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Company",
                        fields: ["name", "company_logo"]
                    }
                })
                .then((r) => (this.companies = r.message || []));
        }
        return this.companies_promise;
    }

    current_logo() {
        const current = this.companies.find((c) => c.name === this.current_company);
        return current ? current.company_logo : null;
    }

    switch_company(company_name) {
        frappe.call({
            method: 'consbiz.api.set_user_default_company',
            args: { company: company_name },
            callback: (r) => { if (r.message) window.location.reload(); }
        });
    }

    // โลโก้บริษัทปัจจุบันในกรอบ avatar ขนาดเดียวกับ Avatar ผู้ใช้
    // ไฟล์โลโก้หาย (เช่นเครื่อง dev ที่ไม่มีไฟล์แนบ) ให้แสดงตัวย่อชื่อบริษัทแทนรูปเสีย
    make_avatar() {
        const logo = this.current_logo();
        const abbr = frappe.get_abbr(this.current_company);
        const frame_html = logo
            ? `<img src="${encodeURI(logo)}" alt="${frappe.utils.escape_html(this.current_company)}">`
            : abbr;

        const $avatar = $(`
            <span class="avatar avatar-medium company-avatar">
                <span class="avatar-frame standard-image">${frame_html}</span>
            </span>`);
        $avatar.find('img').on('error', (e) => $(e.currentTarget).replaceWith(abbr));
        return $avatar;
    }

    make_menu(trigger, side, align) {
        new frappe.ui.Dropdown({
            trigger,
            side,
            align,
            options: [
                {
                    group: __("เปลี่ยนบริษัท"),
                    options: this.companies.map((co) => ({
                        label: co.name,
                        image: co.company_logo || undefined,
                        icon: co.company_logo ? undefined : "building-2",
                        selected: co.name === this.current_company,
                        onclick: () => {
                            if (co.name !== this.current_company) this.switch_company(co.name);
                        }
                    }))
                }
            ]
        });
    }

    // ---------------------------------------------------------------
    // Dock
    // ---------------------------------------------------------------

    render_dock(dock) {
        if (dock.find('.dock-company').length) return;

        const $wrapper = $(`
            <div class="dock-company">
                <button class="dock-item dock-company-button" aria-label="${__("เปลี่ยนบริษัท")}"></button>
            </div>`);
        const $button = $wrapper.find('.dock-company-button').append(this.make_avatar());

        const dock_user = dock.find('.dock-user');
        if (dock_user.length) {
            dock_user.before($wrapper);
        } else {
            dock.append($wrapper);
        }

        this.make_menu($button, "right", "end");

        new frappe.ui.Tooltip($button[0], {
            text: this.current_company,
            side: "right",
            delay: 0,
            offset: 10,
            class: "es-tooltip--plain"
        });
    }

    // ---------------------------------------------------------------
    // Sidebar (ผู้ใช้ที่ปิด Dock)
    // ---------------------------------------------------------------

    render_sidebar(footer) {
        if ($('#sidebar-company-switcher').length) return;

        // ใช้ class เดียวกับแถวผู้ใช้ของ Frappe (sidebar.html) เพื่อให้ได้ขนาด สี hover
        // และการย่อเหลือแค่ avatar ตอนพับ sidebar แบบเดียวกัน
        // Frappe ผูกเมนูผู้ใช้กับ .dropdown-navbar-user ครั้งเดียวตอนสร้าง sidebar ก่อนแถวนี้ถูกแทรก
        const $row = $(`
            <div id="sidebar-company-switcher" class="nav-item dropdown-navbar-user dropdown-mobile mt-3">
                <a class="align-center btn-reset flex nav-link sidebar-user-button"
                    style="width: 100%; min-height: 40px;"
                    aria-label="${__("เปลี่ยนบริษัท")}">
                    <div class="company-avatar-slot"></div>
                    <div class="avatar-name-email overflow-hidden" style="margin-left: 8px;">
                        <span class="d-block text-truncate">${frappe.utils.escape_html(this.current_company)}</span>
                        <span class="d-block text-truncate">${__("เปลี่ยนบริษัท")}</span>
                    </div>
                </a>
            </div>`);
        $row.find('.company-avatar-slot').append(this.make_avatar());

        const user_row = footer.find('.dropdown-navbar-user').not('#sidebar-company-switcher');
        if (user_row.length) {
            user_row.first().before($row);
        } else {
            footer.append($row);
        }

        this.make_menu($row.find('.sidebar-user-button'), "top", "start");
    }
};

$(document).ready(() => { new frappe.ui.CompanySwitcher(); });
