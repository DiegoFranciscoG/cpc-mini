import {Link} from '@astryxdesign/core/Link';
import {DATA_SOURCE, OWNER, OWNER_GITHUB, REPOSITORY} from '../content/site';
import {usePageMeta} from '../meta';
import {ROUTES, RouterLink} from '../router';

const NEW_TAB = '(se abre en otra pestaña)';
const UPDATED = '12 de noviembre de 2026';

export function LegalNotice() {
  usePageMeta('Aviso legal', 'Titular, naturaleza no oficial, condiciones de uso, propiedad intelectual y responsabilidad de CPC-mini.');
  return (
    <article className="doc">
      <h1>Aviso legal</h1>
      <p className="lead">Actualizado el {UPDATED}.</p>
      <section className="doc__section" aria-labelledby="titular">
        <h2 id="titular">Titular</h2>
        <p>
          CPC-mini es un proyecto personal y de código abierto de {OWNER}, en Cuenca, Ecuador. Contacto por{' '}
          <Link href={OWNER_GITHUB} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            GitHub
          </Link>
          .
        </p>
      </section>
      <section className="doc__section" aria-labelledby="no-oficial">
        <h2 id="no-oficial">No es un servicio oficial</h2>
        <p>
          CPC-mini no pertenece al Servicio Nacional de Contratación Pública (SERCOP) ni a ninguna entidad del
          Estado, y no está respaldado por ellas. Sus sugerencias no reemplazan la clasificación que cada entidad
          contratante debe hacer en el Sistema Oficial de Contratación Pública.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="uso">
        <h2 id="uso">Condiciones de uso</h2>
        <p>
          La herramienta es gratuita y se ofrece tal cual, sin garantía de exactitud. Cada sugerencia debe revisarla
          una persona antes de usarla en un proceso de compra, un registro de proveedores o un análisis. No debe
          usarse para decisiones automáticas, sanciones ni auditorías concluyentes. Está prohibido usarla para
          saturar el servicio; las consultas tienen un límite por minuto.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="propiedad">
        <h2 id="propiedad">Propiedad intelectual</h2>
        <p>
          El{' '}
          <Link href={REPOSITORY} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            código fuente
          </Link>{' '}
          se publica con licencia MIT. Los datos del SERCOP conservan su licencia {DATA_SOURCE.licenseShort}; el
          detalle está en <RouterLink to={ROUTES.data}>Datos y licencias</RouterLink>.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="responsabilidad">
        <h2 id="responsabilidad">Responsabilidad</h2>
        <p>
          El titular no responde por decisiones tomadas a partir de las sugerencias ni por interrupciones del
          servicio. Este aviso se rige por las leyes de la República del Ecuador.
        </p>
      </section>
    </article>
  );
}

export function Privacy() {
  usePageMeta('Política de privacidad', 'Qué datos trata CPC-mini, para qué, por cuánto tiempo y cómo ejercer tus derechos según la LOPDP del Ecuador.');
  return (
    <article className="doc">
      <h1>Política de privacidad</h1>
      <p className="lead">
        Actualizada el {UPDATED}. Aplica la Ley Orgánica de Protección de Datos Personales del Ecuador (LOPDP) y su
        principio de minimización: se trata sólo lo indispensable.
      </p>
      <section className="doc__section" aria-labelledby="responsable">
        <h2 id="responsable">Responsable</h2>
        <p>
          {OWNER}, titular del proyecto. Contacto por{' '}
          <Link href={OWNER_GITHUB} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            GitHub
          </Link>
          .
        </p>
      </section>
      <section className="doc__section" aria-labelledby="que-datos">
        <h2 id="que-datos">Qué datos se tratan</h2>
        <ul className="doc__list">
          <li>
            La descripción que escribes: se procesa en memoria para calcular las sugerencias y se descarta al
            responder. No se guarda en bases de datos ni en registros.
          </li>
          <li>
            Tu dirección IP: se mantiene en memoria hasta un minuto para limitar el número de consultas y evitar
            abusos. No se escribe en registros.
          </li>
          <li>
            Registro técnico de cada solicitud: método, ruta, código de respuesta y duración, sin IP ni contenido.
          </li>
        </ul>
        <p>No pidas ni escribas datos personales en la descripción: la herramienta está pensada para productos y servicios.</p>
      </section>
      <section className="doc__section" aria-labelledby="base">
        <h2 id="base">Finalidad y base de legitimación</h2>
        <p>
          Prestar el servicio que solicitas y protegerlo frente a abusos (interés legítimo). No se elaboran perfiles,
          no se toman decisiones automatizadas sobre personas y no se transfieren datos a terceros ni fuera del país.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="derechos">
        <h2 id="derechos">Tus derechos</h2>
        <p>
          Puedes pedir acceso, rectificación, eliminación, oposición o portabilidad de tus datos, aunque el servicio
          no conserva datos que te identifiquen. Si consideras vulnerados tus derechos, puedes acudir a la
          Superintendencia de Protección de Datos Personales.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="datos-publicos">
        <h2 id="datos-publicos">Datos públicos del entrenamiento</h2>
        <p>
          El modelo se entrenó sólo con descripciones de ítems de compras públicas. Se excluyeron las que contenían
          patrones de cédula, RUC de persona natural, teléfono o correo, y no se usaron datos de proveedores.
        </p>
      </section>
    </article>
  );
}

export function Cookies() {
  usePageMeta('Política de cookies', 'CPC-mini no usa cookies ni herramientas de seguimiento. Qué guarda tu navegador y cómo borrarlo.');
  return (
    <article className="doc">
      <h1>Política de cookies</h1>
      <p className="lead">CPC-mini no usa cookies, píxeles, analítica ni herramientas de seguimiento propias o de terceros.</p>
      <section className="doc__section" aria-labelledby="almacenamiento">
        <h2 id="almacenamiento">Lo único que se guarda en tu navegador</h2>
        <p>
          Al pulsar «Entendido» en el aviso, tu navegador guarda en su almacenamiento local la clave{' '}
          <code className="num">cpcmini.aviso-sin-cookies</code> con el valor 1, para no volver a mostrarlo. No sale
          de tu equipo, no te identifica y no se envía al servidor.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="terceros">
        <h2 id="terceros">Sin recursos de terceros</h2>
        <p>
          Las tipografías y los estilos se sirven desde este mismo sitio, así que tu navegador no se conecta a
          servicios externos al cargar la página.
        </p>
      </section>
      <section className="doc__section" aria-labelledby="borrar">
        <h2 id="borrar">Cómo borrarlo</h2>
        <p>
          Desde la configuración de tu navegador, en los datos del sitio, o en modo privado, donde se borra al
          cerrar la ventana. Si un día se añadieran cookies no esenciales, se pedirá tu consentimiento antes.
        </p>
      </section>
    </article>
  );
}

export function NotFound() {
  usePageMeta('Página no encontrada', 'La dirección no existe en CPC-mini.');
  return (
    <article className="doc">
      <h1>Esta página no existe</h1>
      <p className="lead">
        Puede que el enlace esté mal escrito. <RouterLink to={ROUTES.classify}>Volver a clasificar</RouterLink>
      </p>
    </article>
  );
}
