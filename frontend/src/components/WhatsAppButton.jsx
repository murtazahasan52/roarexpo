import { useEventConfig } from "../hooks/useEventConfig";

/**
 * Floating WhatsApp button (bottom-right on every public page).
 * Uses the expo WhatsApp number from event config and opens the WhatsApp
 * app / WhatsApp Web via a wa.me deep link with a prefilled message.
 */
export default function WhatsAppButton() {
  const { config } = useEventConfig();

  const rawNumber = config?.contact?.whatsapp || "";
  const digits = rawNumber.replace(/\D/g, ""); // wa.me needs digits only, intl format
  if (!digits) return null;

  const message = encodeURIComponent(
    `Hello! I'd like to know more about ${config?.eventName || "the expo"}.`
  );
  const href = `https://wa.me/${digits}?text=${message}`;
  const displayNumber = rawNumber.trim();

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="whatsapp-fab"
      aria-label={`Chat with us on WhatsApp at ${displayNumber}`}
      title={`WhatsApp: ${displayNumber}`}
      data-testid="whatsapp-float-button"
    >
      <span className="whatsapp-fab-icon" aria-hidden="true">
        <svg viewBox="0 0 32 32" width="30" height="30" fill="currentColor">
          <path d="M16.004 3.2c-7.06 0-12.8 5.74-12.8 12.8 0 2.256.59 4.46 1.712 6.404L3.2 28.8l6.57-1.72a12.74 12.74 0 0 0 6.234 1.588h.005c7.06 0 12.8-5.74 12.8-12.8 0-3.42-1.332-6.635-3.75-9.054A12.72 12.72 0 0 0 16.004 3.2Zm0 23.02h-.004a10.6 10.6 0 0 1-5.4-1.478l-.388-.23-4.006 1.05 1.07-3.906-.253-.4a10.58 10.58 0 0 1-1.62-5.652c0-5.86 4.77-10.63 10.634-10.63a10.56 10.56 0 0 1 7.51 3.114 10.56 10.56 0 0 1 3.11 7.522c0 5.862-4.77 10.63-10.63 10.63Zm5.83-7.96c-.32-.16-1.89-.932-2.183-1.04-.293-.106-.506-.16-.72.16-.213.32-.826 1.04-1.013 1.253-.187.213-.373.24-.693.08-.32-.16-1.35-.498-2.57-1.586-.95-.847-1.59-1.894-1.777-2.214-.187-.32-.02-.492.14-.652.144-.143.32-.373.48-.56.16-.186.213-.32.32-.533.107-.213.053-.4-.027-.56-.08-.16-.72-1.734-.986-2.374-.26-.624-.523-.54-.72-.55l-.613-.01c-.213 0-.56.08-.853.4-.293.32-1.12 1.094-1.12 2.667 0 1.573 1.146 3.093 1.306 3.307.16.213 2.253 3.44 5.46 4.824.763.33 1.358.527 1.822.674.766.244 1.463.21 2.014.127.615-.092 1.89-.773 2.156-1.52.267-.746.267-1.386.187-1.52-.08-.133-.293-.213-.613-.373Z" />
        </svg>
      </span>
      <span className="whatsapp-fab-label">Chat on WhatsApp</span>
    </a>
  );
}
