import {Link} from '@astryxdesign/core/Link';
import {ATTRIBUTION, DATA_SOURCE, REPOSITORY} from '../content/site';
import {usePageMeta} from '../meta';

const NEW_TAB = '(se abre en otra pestaña)';

const SOFTWARE = [
  {name: 'Código de CPC-mini', license: 'MIT', href: REPOSITORY},
  {name: 'mmBERT-small (codificador, escalón 2)', license: 'MIT', href: 'https://huggingface.co/jhu-clsp/mmBERT-small'},
  {name: 'Qwen3-0.6B-Base (generativo, escalón 3)', license: 'Apache 2.0', href: 'https://huggingface.co/Qwen/Qwen3-0.6B-Base'},
  {name: 'Astryx Design System', license: 'MIT', href: 'https://github.com/meta/astryx'},
  {name: 'Tipografías Red Hat Display, Text y Mono', license: 'SIL Open Font License 1.1', href: 'https://github.com/RedHatOfficial/RedHatFont'},
];

export function DataLicenses() {
  usePageMeta('Datos y licencias', 'Origen de los datos (SERCOP y Open Contracting Partnership), licencia CC BY 3.0 EC y licencias del software.');
  return (
    <article className="doc">
      <h1>Datos y licencias</h1>
      <p className="lead">{ATTRIBUTION}</p>

      <section className="doc__section" aria-labelledby="origen">
        <h2 id="origen">Origen</h2>
        <p>
          Los datos de contratación pública los publica el {DATA_SOURCE.publisher} en su{' '}
          <Link href={DATA_SOURCE.portalUrl} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            portal de datos abiertos
          </Link>
          . CPC-mini usa la copia en formato OCDS del{' '}
          <Link href={DATA_SOURCE.registryUrl} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            {DATA_SOURCE.registry}
          </Link>{' '}
          (publicación 110), años 2015 a 2026, recuperada el 10 de noviembre de 2026.
        </p>
      </section>

      <section className="doc__section" aria-labelledby="licencia">
        <h2 id="licencia">Licencia de los datos</h2>
        <p>
          {DATA_SOURCE.license}. Permite copiar, transformar y usar los datos, incluso comercialmente, con
          atribución, enlace a la licencia e indicación de los cambios.{' '}
          <Link href={DATA_SOURCE.licenseUrl} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            Texto legal de la licencia
          </Link>
          . El uso de los datos no implica respaldo del SERCOP ni de Open Contracting Partnership.
        </p>
      </section>

      <section className="doc__section" aria-labelledby="cambios">
        <h2 id="cambios">Cambios hechos a los datos</h2>
        <ul className="doc__list">
          <li>Se conservan sólo la descripción, el código CPC y el año de cada ítem; no se usan datos de proveedores ni de compradores.</li>
          <li>Se excluyen ítems sin código, descripciones genéricas («ver pliegos») y cualquier texto con patrones de cédula, RUC de persona natural, teléfono o correo.</li>
          <li>Se restaura el cero inicial que pierden los códigos de la sección 0 del CPC.</li>
          <li>Se normaliza el texto, se agrupan descripciones idénticas y se divide por año: entrenamiento hasta 2023, validación 2024, prueba 2025 y 2026.</li>
        </ul>
      </section>

      <section className="doc__section" aria-labelledby="cpc">
        <h2 id="cpc">Sobre el CPC</h2>
        <p>
          El Clasificador Central de Productos agrupa bienes y servicios por niveles. Según el{' '}
          <Link href={DATA_SOURCE.cpcUrl} isExternalLink newTabLabel={NEW_TAB} type="inherit">
            SERCOP
          </Link>
          , un proveedor se registra con un código de 5 dígitos y queda habilitado en los códigos de 9 dígitos que
          contiene. Por eso CPC-mini mide su exactitud en esos dos niveles.
        </p>
      </section>

      <section className="doc__section" aria-labelledby="software">
        <h2 id="software">Software y modelos</h2>
        <div className="table-scroll">
        <table className="sheet-table">
          <caption className="visually-hidden">Licencias del software usado</caption>
          <thead>
            <tr>
              <th scope="col">Componente</th>
              <th scope="col">Licencia</th>
            </tr>
          </thead>
          <tbody>
            {SOFTWARE.map((item) => (
              <tr key={item.name}>
                <th scope="row">
                  <Link href={item.href} isExternalLink newTabLabel={NEW_TAB} type="inherit">
                    {item.name}
                  </Link>
                </th>
                <td>{item.license}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </section>
    </article>
  );
}
