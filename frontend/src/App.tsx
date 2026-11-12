import {lazy, Suspense} from 'react';
import {Skeleton} from '@astryxdesign/core/Skeleton';
import {Shell} from './components/Shell';
import {Classify} from './pages/Classify';
import {ROUTES, usePath} from './router';

const ModelPage = lazy(() => import('./pages/ModelPage').then((m) => ({default: m.ModelPage})));
const DataLicenses = lazy(() => import('./pages/DataLicenses').then((m) => ({default: m.DataLicenses})));
const LegalNotice = lazy(() => import('./pages/Legal').then((m) => ({default: m.LegalNotice})));
const Privacy = lazy(() => import('./pages/Legal').then((m) => ({default: m.Privacy})));
const Cookies = lazy(() => import('./pages/Legal').then((m) => ({default: m.Cookies})));
const NotFound = lazy(() => import('./pages/Legal').then((m) => ({default: m.NotFound})));

function Page({path}: {path: string}) {
  switch (path) {
    case ROUTES.classify:
      return <Classify />;
    case ROUTES.model:
      return <ModelPage />;
    case ROUTES.data:
      return <DataLicenses />;
    case ROUTES.legal:
      return <LegalNotice />;
    case ROUTES.privacy:
      return <Privacy />;
    case ROUTES.cookies:
      return <Cookies />;
    default:
      return <NotFound />;
  }
}

export function App() {
  const path = usePath();
  return (
    <Shell>
      <Suspense fallback={<Skeleton height={240} radius={2} />}>
        <Page path={path} />
      </Suspense>
    </Shell>
  );
}
