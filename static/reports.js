
document.addEventListener("DOMContentLoaded", function () {
    initializeCalendarSelection();

    document.querySelectorAll("[data-print-report]").forEach(function (button) {
        button.addEventListener("click", function () {
            if (typeof Chart !== "undefined") {
                document.querySelectorAll(".report-chart-container canvas").forEach(function (canvas) {
                    const chart = Chart.getChart(canvas);
                    if (!chart) {
                        return;
                    }

                    chart.stop();
                    chart.resize();
                    chart.update("none");
                });
            }

            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    window.print();
                });
            });
        });
    });

    // =====================================
    // 1. LOAD REPORT DATA
    // =====================================

    const reportDataElement = document.getElementById("reportChartData");

    if (!reportDataElement) {
        console.error("Report chart data was not found.");
        return;
    }

    let reportData;

    try {
        reportData = JSON.parse(reportDataElement.textContent);
    } catch (error) {
        console.error("Unable to read report chart data:", error);
        return;
    }

    // Check if Chart.js is available.
    if (typeof Chart === "undefined") {
        console.error("Chart.js library could not be loaded.");
        return;
    }

    reportData.stats = reportData.stats || {};
    reportData.weekly = reportData.weekly || { labels: [], values: [] };
    reportData.monthly = reportData.monthly || { labels: [], values: [] };
    reportData.weekly.labels = reportData.weekly.labels || [];
    reportData.weekly.values = reportData.weekly.values || [];
    reportData.monthly.labels = reportData.monthly.labels || [];
    reportData.monthly.values = reportData.monthly.values || [];


    // =====================================
    // 2. GLOBAL CHART SETTINGS
    // =====================================

    Chart.defaults.color = "#94A3B8";
    Chart.defaults.font.family = 'Inter, "Segoe UI", Arial, sans-serif';

    const gridColor = "rgba(148, 163, 184, 0.12)";

    const chartColors = {
        blue: "#4D9FFF",
        lightBlue: "#69ADFF",
        green: "#34D399",
        yellow: "#FBBF24",
        gray: "#64748B",
        white: "#F1F5F9"
    };


    // =====================================
    // 3. DOUGHNUT CHART CENTER TOTAL
    // =====================================

    const centerTextPlugin = {
        id: "centerText",

        afterDraw(chart) {

            if (chart.config.type !== "doughnut") {
                return;
            }

            const { ctx, chartArea } = chart;

            if (!chartArea) {
                return;
            }

            const total = chart.data.datasets[0].data.reduce(
                (sum, value) => sum + Number(value || 0),
                0
            );

            const centerX = (chartArea.left + chartArea.right) / 2;
            const centerY = (chartArea.top + chartArea.bottom) / 2;

            ctx.save();

            ctx.textAlign = "center";
            ctx.textBaseline = "middle";

            // Total number.
            ctx.font = "bold 30px Arial";
            ctx.fillStyle = chart.$printing ? "#334155" : chartColors.white;

            ctx.fillText(
                total,
                centerX,
                centerY - 8
            );

            // Center label.
            ctx.font = "11px Arial";
            ctx.fillStyle = chart.$printing ? "#475569" : "#94A3B8";

            ctx.fillText(
                "TOTAL ACTIVITIES",
                centerX,
                centerY + 18
            );

            ctx.restore();
        }
    };


    // =====================================
    // 4. TASK STATUS DOUGHNUT CHART
    // =====================================

    const statusCanvas = document.getElementById("statusChart");

    if (statusCanvas && !Chart.getChart(statusCanvas)) {

        const statusValues = [
            Number(reportData.stats.completed || 0),
            Number(reportData.stats.in_progress || 0),
            Number(reportData.stats.pending || 0)
        ];

        new Chart(statusCanvas, {

            type: "doughnut",

            plugins: [centerTextPlugin],

            data: {

                labels: [
                    "Completed",
                    "In Progress",
                    "Pending"
                ],

                datasets: [{

                    data: statusValues,

                    backgroundColor: [
                        chartColors.green,
                        chartColors.yellow,
                        chartColors.gray
                    ],

                    hoverBackgroundColor: [
                        "#6EE7B7",
                        "#FBBF24",
                        "#94A3B8"
                    ],

                    borderColor: "#111827",
                    borderWidth: 4,
                    hoverOffset: 8
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                cutout: "65%",

                plugins: {

                    legend: {
                        position: "bottom",

                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: "circle"
                        }
                    },

                    tooltip: {

                        callbacks: {

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                const total = context.dataset.data.reduce(
                                    (sum, item) => sum + Number(item || 0),
                                    0
                                );

                                const percentage = total > 0
                                    ? ((value / total) * 100).toFixed(1)
                                    : "0.0";

                                return ` ${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        statusCanvas.closest(".chart-canvas-wrapper").dataset.chartReady = "true";
    }


    // =====================================
    // 5. WEEKLY ACTIVITY BAR CHART
    // =====================================

    const weeklyCanvas = document.getElementById("weeklyActivityChart");

    if (weeklyCanvas && !Chart.getChart(weeklyCanvas)) {

        new Chart(weeklyCanvas, {

            type: "bar",

            data: {

                labels: reportData.weekly.labels,

                datasets: [{

                    label: "Activities",

                    data: reportData.weekly.values,

                    backgroundColor: chartColors.blue,
                    hoverBackgroundColor: chartColors.lightBlue,

                    borderRadius: 6,
                    maxBarThickness: 45
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                return ` ${value} ${value === 1 ? "activity" : "activities"}`;
                            }
                        }
                    }
                },

                scales: {

                    x: {

                        grid: {
                            display: false
                        }
                    },

                    y: {

                        beginAtZero: true,

                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },

                        grid: {
                            color: gridColor
                        }
                    }
                }
            }
        });
        weeklyCanvas.closest(".chart-canvas-wrapper").dataset.chartReady = "true";
    }


    // =====================================
    // 6. MONTHLY ACTIVITY BAR CHART
    // =====================================

    const monthlyCanvas = document.getElementById("monthlyActivityChart");

    if (monthlyCanvas && !Chart.getChart(monthlyCanvas)) {

        new Chart(monthlyCanvas, {

            type: "bar",

            data: {

                labels: reportData.monthly.labels.map(
                    date => Number(date.split("-")[2])
                ),

                datasets: [{

                    label: "Activities",

                    data: reportData.monthly.values,

                    backgroundColor: chartColors.blue,
                    hoverBackgroundColor: chartColors.lightBlue,

                    borderRadius: 4,
                    maxBarThickness: 24
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            title: function (items) {

                                return `Day ${items[0].label}`;
                            },

                            label: function (context) {

                                const value = Number(context.raw || 0);

                                return ` ${value} ${value === 1 ? "activity" : "activities"}`;
                            }
                        }
                    }
                },

                scales: {

                    x: {

                        title: {
                            display: true,
                            text: "Day of the Month"
                        },

                        grid: {
                            display: false
                        }
                    },

                    y: {

                        beginAtZero: true,

                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },

                        grid: {
                            color: gridColor
                        }
                    }
                }
            }
        });
        monthlyCanvas.closest(".chart-canvas-wrapper").dataset.chartReady = "true";
    }

    const reportCanvases = [
        statusCanvas,
        weeklyCanvas,
        monthlyCanvas
    ].filter(Boolean);

    window.addEventListener("beforeprint", function () {
        Chart.defaults.color = "#334155";

        reportCanvases.forEach(function (canvas) {
            const chart = Chart.getChart(canvas);

            if (!chart) {
                return;
            }

            chart.$printing = true;
            chart.stop();

            if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = "#334155";
            }

            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(function (scale) {
                    scale.ticks.color = "#334155";
                    if (scale.title) {
                        scale.title.color = "#334155";
                    }
                });
            }

            chart.resize();
            chart.update("none");
        });
    });

    window.addEventListener("afterprint", function () {
        Chart.defaults.color = "#94A3B8";

        reportCanvases.forEach(function (canvas) {
            const chart = Chart.getChart(canvas);

            if (!chart) {
                return;
            }

            chart.$printing = false;

            if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = "#94A3B8";
            }

            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(function (scale) {
                    scale.ticks.color = "#94A3B8";
                    if (scale.title) {
                        scale.title.color = "#94A3B8";
                    }
                });
            }

            chart.resize();
            chart.update("none");
        });
    });

});

function initializeCalendarSelection() {
    const calendarButtons = document.querySelectorAll("[data-calendar-date]");
    const modal = document.getElementById("calendar-activity-modal");
    const modalDate = document.getElementById("calendar-modal-date");
    const modalCount = document.getElementById("calendar-modal-count");
    const modalActivities = document.getElementById("calendar-modal-activities");
    const modalEmptyState = document.getElementById("calendar-modal-empty");
    const closeButton = modal
        ? modal.querySelector("[data-calendar-modal-close]")
        : null;

    if (!modal || !modalDate || !modalCount || !modalActivities || !modalEmptyState) {
        return;
    }

    const activityItems = Array.from(
        modalActivities.querySelectorAll("[data-calendar-activity]")
    );
    let activeTrigger = null;

    function closeCalendarModal() {
        if (modal.open) {
            modal.close();
        }
    }

    calendarButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const selectedDate = button.dataset.calendarDate;
            const date = new Date(`${selectedDate}T12:00:00`);
            const matchingActivities = activityItems.filter(function (item) {
                const isMatch = item.dataset.calendarActivity === selectedDate;
                item.hidden = !isMatch;
                return isMatch;
            });

            calendarButtons.forEach(function (calendarButton) {
                calendarButton.setAttribute(
                    "aria-pressed",
                    String(calendarButton === button)
                );
            });

            modalDate.textContent = new Intl.DateTimeFormat(undefined, {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric"
            }).format(date);
            modalCount.textContent =
                `${matchingActivities.length} matching ${matchingActivities.length === 1 ? "activity" : "activities"}`;
            modalEmptyState.hidden = matchingActivities.length > 0;
            activeTrigger = button;
            modal.showModal();
        });
    });

    if (closeButton) {
        closeButton.addEventListener("click", closeCalendarModal);
    }

    window.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.open) {
            event.preventDefault();
            closeCalendarModal();
        }
    });

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeCalendarModal();
        }
    });

    modal.addEventListener("close", function () {
        calendarButtons.forEach(function (button) {
            button.setAttribute("aria-pressed", "false");
        });

        if (activeTrigger && activeTrigger.isConnected) {
            activeTrigger.focus();
        }

        activeTrigger = null;
    });

    window.addEventListener("beforeprint", closeCalendarModal);
}
